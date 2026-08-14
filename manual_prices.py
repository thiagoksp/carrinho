"""Create and import manual price observations without changing planning."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import unicodedata

from catalog import Product, load_simulated_catalog
from pilot import PILOT_LOCATION, PILOT_STORE


CSV_FIELDS = (
    "key",
    "product_reference",
    "observed_package",
    "price_cad",
    "observed_on",
    "store_location",
    "channel",
    "price_type",
    "quantity_mode",
    "declared_source",
)
SNAPSHOT_SCHEMA = "carrinho.manual-price-observations.v3"
PILOT_CURRENCY = "CAD"
MAX_CSV_SIZE = 1_000_000
MAX_PRICE_CENTS = 1_000_000
TEMPLATE_DELIMITER = ","
ALLOWED_CHANNELS = frozenset(
    {"official-site", "store-label", "final-receipt"}
)
SUPPORTED_PRICE_TYPE = "regular"
QUANTITY_MODES = frozenset({"fixed-package", "final-receipt-weight"})
SNAPSHOT_NOTICE = (
    "Manual, historical, and self-declared record. The hash confirms only "
    "the bytes of the imported CSV, not the authenticity of the price. This "
    "is not a live price, licensed source, verified value, or availability "
    "guarantee. Planning continues to use one simulated price source, and "
    "this observation cannot affect it."
)


class PriceImportErrors(ValueError):
    """Group all CSV problems so the user can correct them together."""

    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("\n".join(errors))


@dataclass(frozen=True)
class ImportResult:
    path: Path
    count: int
    total_products: int
    warnings: tuple[str, ...]


def _outputs_directory() -> Path:
    return Path(__file__).resolve().parent / "outputs"


def _next_path(path: Path) -> Path:
    if not path.exists():
        return path

    number = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{number}{path.suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def create_csv_template(path: Path | None = None) -> Path:
    """Create an Excel-compatible CSV without replacing an earlier template."""
    destination = path or _outputs_directory() / "no-frills-toronto-prices.csv"
    destination = _next_path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    catalog = load_simulated_catalog()
    with destination.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
            delimiter=TEMPLATE_DELIMITER,
            lineterminator="\n",
        )
        writer.writeheader()
        for product in catalog.products:
            writer.writerow(
                {
                    "key": product.key,
                    "product_reference": product.name,
                    "observed_package": "",
                    "price_cad": "",
                    "observed_on": "",
                    "store_location": "",
                    "channel": "",
                    "price_type": "",
                    "quantity_mode": "",
                    "declared_source": "",
                }
            )
    return destination


def _contains_control_character(text: str) -> bool:
    return any(
        unicodedata.category(character).startswith("C") for character in text
    )


def _is_unsafe_spreadsheet_text(text: str) -> bool:
    trimmed = text.lstrip()
    return _contains_control_character(text) or bool(
        trimmed and trimmed[0] in "=+-@"
    )


def _contains_sensitive_identifier(text: str) -> bool:
    email = re.search(
        r"\b[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b",
        text,
        re.IGNORECASE,
    )
    phone = re.search(
        r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)",
        text,
    )
    long_number = re.search(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text)
    labelled_identifier = re.search(
        r"\b(?:order|receipt|transaction|card)\s+"
        r"(?:number|no\.?|id|#)\s*[:#-]?\s*[A-Z0-9-]*\d[A-Z0-9-]*\b",
        text,
        re.IGNORECASE,
    )
    return any((email, phone, long_number, labelled_identifier))


def _parse_price_cents(text: str) -> int:
    value = text.strip()
    if any(character.isspace() for character in value) or len(value) > 12:
        raise ValueError("use a value such as 5.99 or 5,99")
    if value.upper().startswith("CAD$"):
        value = value[4:]
    elif value.startswith("$"):
        value = value[1:]

    if (
        not value
        or value[0] in "=+@-"
        or ("," in value and "." in value)
    ):
        raise ValueError("use a value such as 5.99 or 5,99")
    if not re.fullmatch(r"\d+(?:[.,]\d{1,2})?", value):
        raise ValueError("use a value such as 5.99 or 5,99")

    try:
        decimal = Decimal(value.replace(",", "."))
    except InvalidOperation as error:
        raise ValueError("use a value such as 5.99 or 5,99") from error
    if not decimal.is_finite() or decimal <= 0:
        raise ValueError("the price must be greater than zero")
    cents = int(decimal * 100)
    if cents > MAX_PRICE_CENTS:
        raise ValueError("the price must be at most CAD$10,000.00")
    return cents


def _parse_observation_date(text: str, today: date) -> date:
    value = text.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            observed = date.fromisoformat(value)
        elif re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
            observed = datetime.strptime(value, "%m/%d/%Y").date()
        else:
            raise ValueError
    except ValueError as error:
        raise ValueError("use YYYY-MM-DD or M/D/YYYY") from error
    if observed > today:
        raise ValueError("the observation date cannot be in the future")
    return observed


def _detect_delimiter(text: str) -> str:
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    for delimiter in (",", ";"):
        try:
            header = next(
                csv.reader([first_line], delimiter=delimiter, strict=True)
            )
        except csv.Error:
            continue
        if tuple(header) == CSV_FIELDS:
            return delimiter
    raise PriceImportErrors(
        [
            "the header was changed; run create-template again and copy only "
            "the observations"
        ]
    )


def _read_csv(path: Path) -> tuple[list[dict[object, object]], bytes]:
    content = path.read_bytes()
    if len(content) > MAX_CSV_SIZE:
        raise PriceImportErrors(["the file exceeds the 1 MB limit"])
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise PriceImportErrors(["the file must be saved as UTF-8"]) from error

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(
        io.StringIO(text, newline=""), delimiter=delimiter, strict=True
    )
    try:
        rows = list(reader)
    except csv.Error as error:
        raise PriceImportErrors(
            ["the CSV is malformed; open the template in Excel and save it again"]
        ) from error
    return rows, content


def _validate_row(
    row: dict[str, str],
    number: int,
    expected_product: Product,
    today: date,
) -> tuple[dict[str, object] | None, list[str], str | None]:
    errors: list[str] = []
    key = row["key"].strip()
    if row["product_reference"].strip() != expected_product.name:
        errors.append(f"row {number} ({key}): do not change the product name")

    editable_values = (
        row["observed_package"],
        row["price_cad"],
        row["observed_on"],
        row["store_location"],
        row["channel"],
        row["price_type"],
        row["quantity_mode"],
        row["declared_source"],
    )
    if not any(value.strip() for value in editable_values):
        return None, errors, None

    observed_package = row["observed_package"].strip()
    price_text = row["price_cad"].strip()
    date_text = row["observed_on"].strip()
    store_location = row["store_location"].strip()
    channel = row["channel"].strip().casefold()
    price_type = row["price_type"].strip().casefold()
    quantity_mode = row["quantity_mode"].strip().casefold()
    declared_source = row["declared_source"].strip()

    if not observed_package:
        errors.append(f"row {number} ({key}): provide the observed package")
    elif (
        _is_unsafe_spreadsheet_text(observed_package)
        or len(observed_package) > 120
    ):
        errors.append(f"row {number} ({key}): invalid observed package")
    if not price_text:
        errors.append(f"row {number} ({key}): price is empty")
    if not date_text:
        errors.append(f"row {number} ({key}): provide the observation date")
    if not store_location:
        errors.append(f"row {number} ({key}): provide the store location")
    elif (
        _is_unsafe_spreadsheet_text(store_location)
        or len(store_location) > 200
    ):
        errors.append(f"row {number} ({key}): invalid store location")
    else:
        normalized_store = store_location.casefold()
        has_identifier = bool(
            re.search(r"\b\d{1,5}\b", store_location)
            or re.search(
                r"\b[A-Z]\d[A-Z][ -]?\d[A-Z]\d\b",
                store_location,
                re.IGNORECASE,
            )
        )
        if (
            "no frills" not in normalized_store
            or "toronto" not in normalized_store
            or not has_identifier
        ):
            errors.append(
                f"row {number} ({key}): provide the address or postal code "
                "of a No Frills location in Toronto"
            )
    if not channel:
        errors.append(f"row {number} ({key}): provide the channel")
    elif channel not in ALLOWED_CHANNELS:
        options = ", ".join(sorted(ALLOWED_CHANNELS))
        errors.append(f"row {number} ({key}): channel must be {options}")
    if price_type != SUPPORTED_PRICE_TYPE:
        errors.append(
            f"row {number} ({key}): only regular price_type is accepted"
        )
    if quantity_mode not in QUANTITY_MODES:
        options = ", ".join(sorted(QUANTITY_MODES))
        errors.append(
            f"row {number} ({key}): quantity_mode must be {options}"
        )
    elif quantity_mode == "final-receipt-weight" and channel != "final-receipt":
        errors.append(
            f"row {number} ({key}): final-receipt-weight requires the "
            "final-receipt channel"
        )
    if not declared_source:
        errors.append(f"row {number} ({key}): provide the declared source")
    elif (
        _is_unsafe_spreadsheet_text(declared_source)
        or _contains_sensitive_identifier(declared_source)
        or len(declared_source) > 500
    ):
        errors.append(f"row {number} ({key}): invalid declared source")

    promotion_context = f"{observed_package} {declared_source}".casefold()
    promotion_markers = (
        "promo",
        "sale",
        "clearance",
        "discount",
        "coupon",
        "member",
        "pc optimum",
        "multi-buy",
        "multibuy",
        "bogo",
        "buy one get one",
    )
    multi_buy_pattern = re.compile(
        r"\b(?:buy\s+)?\d+\s+for\s+(?:cad\$|\$)?\s*\d|"
        r"\b\d+\s*/\s*(?:cad\$|\$)?\s*\d|"
        r"\bbuy\s+\d+\b|\bget\s+\d+\s+free\b",
        re.IGNORECASE,
    )
    if (
        any(marker in promotion_context for marker in promotion_markers)
        or multi_buy_pattern.search(promotion_context)
    ):
        errors.append(
            f"row {number} ({key}): promotions, coupons, member prices, "
            "and multi-buy offers are not accepted"
        )

    price_cents: int | None = None
    observed_on: date | None = None
    if price_text:
        try:
            price_cents = _parse_price_cents(price_text)
        except ValueError as error:
            errors.append(f"row {number} ({key}): {error}")
    if date_text:
        try:
            observed_on = _parse_observation_date(date_text, today)
        except ValueError as error:
            errors.append(f"row {number} ({key}): {error}")

    if errors or price_cents is None or observed_on is None:
        return None, errors, None

    age = (today - observed_on).days
    warning = None
    if age > 7:
        warning = f"{key}: observation was made {age} days ago"
    return (
        {
            "csv_row": number,
            "product_key": key,
            "product_reference": expected_product.name,
            "observed_package": observed_package,
            "price_cents": price_cents,
            "observed_on": observed_on.isoformat(),
            "declared_store_location": store_location,
            "declared_channel": channel,
            "declared_price_type": price_type,
            "declared_quantity_mode": quantity_mode,
            "declared_source": declared_source,
        },
        errors,
        warning,
    )


def _build_snapshot(
    observations: list[dict[str, object]],
    csv_path: Path,
    csv_content: bytes,
    now: datetime,
) -> dict[str, object]:
    return {
        "schema": SNAPSHOT_SCHEMA,
        "type": "manual-price-observations",
        "currency": PILOT_CURRENCY,
        "target_retailer": PILOT_STORE,
        "target_region": PILOT_LOCATION,
        "method": "manual user declaration",
        "imported_at": now.astimezone(timezone.utc).isoformat(),
        "source_file": {
            "name": csv_path.name,
            "sha256": hashlib.sha256(csv_content).hexdigest(),
        },
        "observations": observations,
        "notice": SNAPSHOT_NOTICE,
    }


def _latest_template() -> Path:
    directory = _outputs_directory()
    candidates = list(directory.glob("no-frills-toronto-prices*.csv"))
    if not candidates:
        return directory / "no-frills-toronto-prices.csv"
    return max(
        candidates,
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )


def import_prices_csv(
    csv_path: Path | None = None,
    output_directory: Path | None = None,
    *,
    today: date | None = None,
    now: datetime | None = None,
) -> ImportResult:
    """Validate price declarations and create an isolated local record."""
    current_date = today or date.today()
    current_time = now or datetime.now(timezone.utc)
    source = csv_path or _latest_template()
    if not source.is_file():
        raise PriceImportErrors(
            [f"file not found: {source}", "first run: create-template"]
        )

    rows, content = _read_csv(source)
    catalog = load_simulated_catalog()
    expected_products = {product.key: product for product in catalog.products}
    seen: set[str] = set()
    errors: list[str] = []
    observations: list[dict[str, object]] = []
    warnings: list[str] = []

    for number, raw_row in enumerate(rows, start=2):
        if None in raw_row:
            errors.append(
                f"row {number}: extra columns found; do not add new fields"
            )
            continue
        if any(raw_row.get(field) is None for field in CSV_FIELDS):
            errors.append(f"row {number}: template columns are missing")
            continue
        row = {field: str(raw_row[field]) for field in CSV_FIELDS}
        if not any(value.strip() for value in row.values()):
            continue
        key = row["key"].strip()
        if key not in expected_products:
            errors.append(f"row {number}: unknown key: {key or '(empty)'}")
            continue
        if key in seen:
            errors.append(f"row {number} ({key}): duplicate key")
            continue
        seen.add(key)
        observation, row_errors, warning = _validate_row(
            row, number, expected_products[key], current_date
        )
        errors.extend(row_errors)
        if observation is not None:
            observations.append(observation)
        if warning is not None:
            warnings.append(warning)

    missing = sorted(set(expected_products).difference(seen))
    if missing:
        errors.append(f"template rows are missing: {', '.join(missing)}")
    store_locations = {
        re.sub(
            r"\s+",
            " ",
            str(observation["declared_store_location"]).strip().casefold(),
        )
        for observation in observations
    }
    if len(store_locations) > 1:
        errors.append(
            "all observations must use the same exact No Frills store location"
        )
    if not observations and not errors:
        errors.append("provide at least one complete observation")
    if errors:
        raise PriceImportErrors(errors)

    directory = output_directory or _outputs_directory()
    directory.mkdir(parents=True, exist_ok=True)
    name = f"manual-price-observations-{current_date.isoformat()}.json"
    destination = _next_path(directory / name)
    snapshot = _build_snapshot(observations, source, content, current_time)
    destination.write_text(
        f"{json.dumps(snapshot, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    return ImportResult(
        path=destination,
        count=len(observations),
        total_products=len(expected_products),
        warnings=tuple(warnings),
    )


def _show_usage() -> None:
    print("Usage:")
    print("  python manual_prices.py create-template")
    print("  python manual_prices.py import")


def main(arguments: list[str] | None = None) -> int:
    args = arguments if arguments is not None else sys.argv[1:]
    if args == ["create-template"]:
        default_path = _outputs_directory() / "no-frills-toronto-prices.csv"
        path = create_csv_template(default_path)
        print(f"\nTemplate created at:\n{path}")
        print(
            "Open it in Excel and complete the observed fields for one product. "
            "The other rows can remain empty."
        )
        return 0
    if args == ["import"]:
        try:
            result = import_prices_csv()
        except PriceImportErrors as error:
            print("\nNothing was imported:")
            for message in error.errors:
                print(f"- {message}")
            return 1

        print(
            f"\n{result.count} of {result.total_products} observed price(s) "
            "were recorded."
        )
        print(f"Snapshot saved at:\n{result.path}")
        for warning in result.warnings:
            print(f"Warning: {warning}.")
        print("Planning continues to use one simulated price source.")
        return 0

    _show_usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
