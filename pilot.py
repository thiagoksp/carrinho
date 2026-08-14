"""Define the single retailer and market supported by the current pilot."""

import re


PILOT_STORE = "No Frills"
PILOT_LOCATION = "Toronto, ON"


def matches_pilot_store(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().casefold() == PILOT_STORE.casefold()


def matches_pilot_location(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().casefold()
    if "toronto" in normalized:
        return True
    return bool(
        re.search(
            r"\bM\d[A-Z][ -]?\d[A-Z]\d\b",
            value,
            re.IGNORECASE,
        )
    )
