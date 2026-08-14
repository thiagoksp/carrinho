"""Load and validate Carrinho price catalogs."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import unicodedata


INSTACART_UNITS = {"kg", "g", "can", "lb bag", "each", "ml", "package"}


@dataclass(frozen=True)
class Product:
    key: str
    name: str
    package_description: str
    package_size: float
    package_price: float
    keywords: tuple[str, ...]
    instacart_search_term: str
    instacart_quantity: float
    instacart_unit: str


@dataclass(frozen=True)
class PriceCatalog:
    currency: str
    price_type: str
    description: str
    products: tuple[Product, ...]


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.strip().casefold())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def _validate_product(data: object, position: int) -> Product:
    if not isinstance(data, dict):
        raise ValueError(f"Product {position} must be an object.")

    fields = {
        "key",
        "name",
        "package_description",
        "package_size",
        "package_price",
        "keywords",
        "instacart_search_term",
        "instacart_quantity",
        "instacart_unit",
    }
    missing_fields = fields.difference(data)
    if missing_fields:
        raise ValueError(
            f"Product {position} is missing: "
            f"{', '.join(sorted(missing_fields))}."
        )

    try:
        package_size = float(data["package_size"])
        package_price = float(data["package_price"])
        instacart_quantity = float(data["instacart_quantity"])
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Product {position} has an invalid quantity or price."
        ) from error

    text_fields = (
        "key",
        "name",
        "package_description",
        "instacart_search_term",
        "instacart_unit",
    )
    if any(
        not isinstance(data[field], str) or not data[field].strip()
        for field in text_fields
    ):
        raise ValueError(f"Product {position} has an empty required text field.")

    keywords = data["keywords"]
    if (
        not math.isfinite(package_size)
        or not math.isfinite(package_price)
        or not math.isfinite(instacart_quantity)
    ):
        raise ValueError(f"Product {position} has an invalid quantity or price.")
    if package_size <= 0 or package_price < 0 or instacart_quantity <= 0:
        raise ValueError(f"Product {position} has an invalid quantity or price.")
    if (
        not isinstance(keywords, list)
        or not keywords
        or any(
            not isinstance(keyword, str) or not keyword.strip()
            for keyword in keywords
        )
    ):
        raise ValueError(f"Product {position} requires at least one keyword.")

    instacart_unit = data["instacart_unit"].strip()
    if instacart_unit not in INSTACART_UNITS:
        raise ValueError(f"Product {position} has an unsupported Instacart unit.")

    return Product(
        key=_normalize_text(data["key"]),
        name=data["name"].strip(),
        package_description=data["package_description"].strip(),
        package_size=package_size,
        package_price=package_price,
        keywords=tuple(_normalize_text(keyword) for keyword in keywords),
        instacart_search_term=data["instacart_search_term"].strip(),
        instacart_quantity=instacart_quantity,
        instacart_unit=instacart_unit,
    )


def load_catalog(path: Path) -> PriceCatalog:
    """Load a JSON catalog and fail early when its data is invalid."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("The catalog must be a JSON object.")

    raw_products = data.get("products")
    if not isinstance(raw_products, list) or not raw_products:
        raise ValueError("The catalog must contain products.")

    products = tuple(
        _validate_product(product, position)
        for position, product in enumerate(raw_products, start=1)
    )
    keys = [product.key for product in products]
    if len(keys) != len(set(keys)):
        raise ValueError("The catalog contains duplicate product keys.")

    currency = str(data.get("currency", "")).strip().upper()
    price_type = str(data.get("price_type", "")).strip().casefold()
    description = str(data.get("description", "")).strip()
    if not currency or not price_type or not description:
        raise ValueError(
            "The catalog must include currency, price type, and description."
        )

    return PriceCatalog(
        currency=currency,
        price_type=price_type,
        description=description,
        products=products,
    )


def load_simulated_catalog() -> PriceCatalog:
    path = Path(__file__).resolve().parent / "data" / "simulated-prices.json"
    return load_catalog(path)
