"""Validate the single-store integration configuration for Carrinho."""

from dataclasses import dataclass
import json
from pathlib import Path
import re

from catalog import load_catalog


PRICE_SOURCES = {"simulated", "licensed"}
LIST_DELIVERY_METHODS = {"none", "instacart"}
STATUSES = {"planned", "development", "available"}
PILOT_INTEGRATION_ID = "no-frills-toronto"
INTEGRATION_FIELDS = frozenset(
    {
        "id",
        "pilot_store",
        "pilot_location",
        "country",
        "currency",
        "price_source",
        "price_status",
        "local_catalog",
        "list_delivery",
        "delivery_status",
        "supports_store_selection",
        "real_prices_available",
        "notice",
    }
)


@dataclass(frozen=True)
class StoreIntegration:
    id: str
    pilot_store: str
    pilot_location: str
    country: str
    currency: str
    price_source: str
    price_status: str
    local_catalog: Path
    list_delivery: str
    delivery_status: str
    supports_store_selection: bool
    real_prices_available: bool
    notice: str

    @property
    def can_use_real_prices(self) -> bool:
        return (
            self.price_source == "licensed"
            and self.price_status == "available"
            and self.real_prices_available
        )

    @property
    def can_deliver_list(self) -> bool:
        return (
            self.list_delivery != "none"
            and self.delivery_status == "available"
        )


def _required_text(data: dict[str, object], field: str, position: int) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Integration {position} must provide a non-empty {field} field."
        )
    return value.strip()


def _validate_local_catalog(
    configured_path: str,
    data_directory: Path,
    price_source: str,
    currency: str,
    position: int,
) -> Path:
    relative_path = Path(configured_path)
    if relative_path.is_absolute():
        raise ValueError(
            f"Integration {position} has a catalog outside the data directory."
        )

    resolved_directory = data_directory.resolve()
    resolved_path = (resolved_directory / relative_path).resolve()
    if not resolved_path.is_relative_to(resolved_directory):
        raise ValueError(
            f"Integration {position} has a catalog outside the data directory."
        )
    if not resolved_path.is_file():
        raise ValueError(
            f"Integration {position} points to a catalog that does not exist."
        )

    catalog = load_catalog(resolved_path)
    if catalog.currency != currency:
        raise ValueError(
            f"Integration {position} uses a catalog in another currency."
        )
    if price_source == "simulated" and catalog.price_type != "simulated":
        raise ValueError(
            f"Integration {position} must use a catalog labelled as simulated."
        )
    if price_source == "licensed" and catalog.price_type != "licensed":
        raise ValueError(
            f"Integration {position} must use a catalog labelled as licensed."
        )
    return resolved_path


def _validate_integration(
    data: object, position: int, data_directory: Path
) -> StoreIntegration:
    if not isinstance(data, dict):
        raise ValueError(f"Integration {position} must be a JSON object.")

    unsupported_fields = sorted(set(data).difference(INTEGRATION_FIELDS))
    if unsupported_fields:
        raise ValueError(
            f"Integration {position} contains unsupported fields: "
            f"{', '.join(unsupported_fields)}."
        )

    identifier = _required_text(data, "id", position)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
        raise ValueError(f"Integration {position} has an invalid id.")

    country = _required_text(data, "country", position).upper()
    currency = _required_text(data, "currency", position).upper()
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise ValueError(f"Integration {position} has an invalid country code.")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError(f"Integration {position} has an invalid currency code.")

    price_source = _required_text(data, "price_source", position)
    list_delivery = _required_text(data, "list_delivery", position)
    price_status = _required_text(data, "price_status", position)
    delivery_status = _required_text(data, "delivery_status", position)
    if price_source not in PRICE_SOURCES:
        raise ValueError(f"Integration {position} has an invalid price source.")
    if list_delivery not in LIST_DELIVERY_METHODS:
        raise ValueError(
            f"Integration {position} has an invalid list delivery method."
        )
    if price_status not in STATUSES:
        raise ValueError(f"Integration {position} has an invalid price status.")
    if delivery_status not in STATUSES:
        raise ValueError(
            f"Integration {position} has an invalid delivery status."
        )

    real_prices_available = data.get("real_prices_available")
    if not isinstance(real_prices_available, bool):
        raise ValueError(
            f"Integration {position} must declare real_prices_available."
        )
    if real_prices_available and price_source != "licensed":
        raise ValueError(
            "Real prices can only be enabled with one licensed price source."
        )
    if real_prices_available and price_status != "available":
        raise ValueError("Real prices require an available price source.")

    supports_store_selection = data.get("supports_store_selection")
    if not isinstance(supports_store_selection, bool):
        raise ValueError(
            f"Integration {position} must declare supports_store_selection."
        )
    if list_delivery == "instacart" and supports_store_selection:
        raise ValueError(
            "The Instacart integration cannot guarantee a specific store."
        )
    if delivery_status == "available" and list_delivery == "none":
        raise ValueError(
            "An available integration must define a list delivery method."
        )

    local_catalog = _validate_local_catalog(
        _required_text(data, "local_catalog", position),
        data_directory,
        price_source,
        currency,
        position,
    )

    return StoreIntegration(
        id=identifier,
        pilot_store=_required_text(data, "pilot_store", position),
        pilot_location=_required_text(data, "pilot_location", position),
        country=country,
        currency=currency,
        price_source=price_source,
        price_status=price_status,
        local_catalog=local_catalog,
        list_delivery=list_delivery,
        delivery_status=delivery_status,
        supports_store_selection=supports_store_selection,
        real_prices_available=real_prices_available,
        notice=_required_text(data, "notice", position),
    )


def load_integrations(path: Path) -> tuple[StoreIntegration, ...]:
    """Load and validate the local single-store integration registry."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("The integration registry must be a JSON object.")

    records = data.get("integrations")
    if not isinstance(records, list) or not records:
        raise ValueError("The registry must contain integrations.")

    integrations = tuple(
        _validate_integration(record, position, path.resolve().parent)
        for position, record in enumerate(records, start=1)
    )
    identifiers = [integration.id for integration in integrations]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("The registry contains duplicate integration ids.")
    return integrations


def load_pilot_integration() -> StoreIntegration:
    path = Path(__file__).resolve().parent / "data" / "store-integrations.json"
    integrations = load_integrations(path)
    for integration in integrations:
        if integration.id == PILOT_INTEGRATION_ID:
            return integration
    raise ValueError("The pilot integration was not found.")
