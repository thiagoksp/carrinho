"""Canonical pantry candidates for Carrinho."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import unicodedata

from catalog import Product, resolve_product_keys


PANTRY_SOURCES = {"text", "quick_select", "voice", "photo"}
QUANTITY_STATES = {"known", "unknown", "invalid"}
RESOLUTION_STATES = {"matched", "unmatched"}

_NUMBER_WORD_VALUES = {
    "half": 0.5,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
}
_UNIT_ALIASES = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "ml": "ml",
    "l": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
    "can": "can",
    "cans": "can",
    "package": "package",
    "packages": "package",
    "pack": "package",
    "packs": "package",
    "bag": "package",
    "bags": "package",
    "dozen": "dozen",
    "dozens": "dozen",
}


@dataclass(frozen=True)
class PantryCandidate:
    name: str
    food_key: str | None
    original_text: str
    quantity_value: float | None
    quantity_unit: str | None
    quantity_state: str
    resolution_state: str
    source: str
    needs_review: bool


def _remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def _split_entries(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[\r\n,]+|\s+and\s+|\s+or\s+", value, flags=re.IGNORECASE)
        if item.strip()
    ]


def _parse_amount_value(text: str) -> float | None:
    normalized = _remove_accents(text)
    fraction = re.search(r"\b(\d+)\s*/\s*(\d+)\b", normalized)
    if fraction and int(fraction.group(2)) != 0:
        return int(fraction.group(1)) / int(fraction.group(2))

    number = re.search(r"\b\d+(?:[.,]\d+)?\b", normalized)
    if number:
        return float(number.group().replace(",", "."))

    for word, value in _NUMBER_WORD_VALUES.items():
        if re.search(rf"\b{word}\b", normalized):
            return value
    return None


def _parse_entry(entry: str) -> tuple[str, float | None, str | None]:
    text = entry.strip()
    normalized = _remove_accents(text)
    if not normalized:
        return "", None, None

    tokens = normalized.split()
    if not tokens:
        return "", None, None

    amount = _parse_amount_value(tokens[0])
    if amount is None:
        if tokens[0] in {"enough", "some", "any", "extra", "leftover", "leftovers"} and len(tokens) > 1:
            name = " ".join(text.split()[1:]).strip()
            return name or text, None, None
        return text, None, None

    index = 1
    if index < len(tokens) and tokens[index] in {"a", "an"}:
        index += 1

    unit_token = None
    if index < len(tokens) and tokens[index] in _UNIT_ALIASES:
        unit_token = tokens[index]
        index += 1

    if index < len(tokens) and tokens[index] == "of":
        index += 1

    name = " ".join(text.split()[index:]).strip()
    if not name:
        name = text

    return name, amount, _UNIT_ALIASES.get(unit_token) if unit_token else None


def _resolve_candidate_name(name: str, products: tuple[Product, ...]) -> tuple[str | None, str]:
    try:
        resolved = resolve_product_keys([name], products)
    except ValueError:
        return None, name
    if not resolved:
        return None, name
    product_key = resolved[0]
    product = next(product for product in products if product.key == product_key)
    return product.key, product.name


def parse_pantry_candidates(
    value: str | list[str] | tuple[str, ...] | None,
    products: tuple[Product, ...],
    *,
    source: str = "text",
) -> tuple[PantryCandidate, ...]:
    if source not in PANTRY_SOURCES:
        raise ValueError("Unsupported pantry source.")
    if value is None:
        return ()
    entries = _split_entries(value) if isinstance(value, str) else [item.strip() for item in value if str(item).strip()]
    candidates: list[PantryCandidate] = []
    for entry in entries:
        original_text = str(entry).strip()
        if not original_text:
            continue
        name, amount, quantity_unit = _parse_entry(original_text)
        food_key, resolved_name = _resolve_candidate_name(name, products) if name else (None, name)
        resolution_state = "matched" if food_key is not None else "unmatched"
        quantity_state = "unknown"
        needs_review = True
        if amount is not None:
            if food_key is None:
                quantity_state = "invalid"
            else:
                product = next(product for product in products if product.key == food_key)
                if product.planning_unit == "each" and quantity_unit is None:
                    quantity_state = "known"
                    quantity_unit = "each"
                elif product.planning_unit == "g" and quantity_unit in {"g", "kg", "lb", "package"}:
                    quantity_state = "known"
                elif product.planning_unit == "ml" and quantity_unit in {"ml", "l"}:
                    quantity_state = "known"
                elif product.planning_unit == "can" and quantity_unit in {"can", "package"}:
                    quantity_state = "known"
                elif product.planning_unit == "package" and quantity_unit == "package":
                    quantity_state = "known"
                elif product.planning_unit == "each" and quantity_unit in {"each", "dozen"}:
                    quantity_state = "known"
                else:
                    quantity_state = "invalid"
        if food_key is not None and quantity_state == "known":
            needs_review = False
        candidate = PantryCandidate(
            name=resolved_name or name or original_text,
            food_key=food_key,
            original_text=original_text,
            quantity_value=amount,
            quantity_unit=quantity_unit,
            quantity_state=quantity_state,
            resolution_state=resolution_state,
            source=source,
            needs_review=needs_review,
        )
        candidates.append(candidate)
    return tuple(candidates)


def pantry_candidates_to_json(candidates: tuple[PantryCandidate, ...] | list[PantryCandidate]) -> str:
    return json.dumps([candidate.__dict__ for candidate in candidates], ensure_ascii=False)


def pantry_candidates_from_json(value: str, products: tuple[Product, ...], *, source: str = "text") -> tuple[PantryCandidate, ...]:
    if not value.strip():
        return ()
    raw_items = json.loads(value)
    if not isinstance(raw_items, list):
        raise ValueError("Pantry items must be a JSON list.")
    candidates: list[PantryCandidate] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError("Pantry items must contain JSON objects.")
        original_text = str(raw_item.get("original_text", "")).strip()
        if not original_text:
            raise ValueError("Pantry items must include original text.")
        name = str(raw_item.get("name", original_text)).strip() or original_text
        food_key = str(raw_item.get("food_key", "")).strip() or None
        quantity_raw = raw_item.get("quantity_value")
        if quantity_raw in {"", None}:
            quantity_value = None
        else:
            quantity_value = float(quantity_raw)
        quantity_unit = str(raw_item.get("quantity_unit", "")).strip() or None
        quantity_state = str(raw_item.get("quantity_state", "unknown")).strip()
        resolution_state = str(raw_item.get("resolution_state", "unmatched")).strip()
        needs_review = bool(raw_item.get("needs_review", True))
        if quantity_state not in QUANTITY_STATES:
            raise ValueError("Pantry items have an invalid quantity state.")
        if resolution_state not in RESOLUTION_STATES:
            raise ValueError("Pantry items have an invalid resolution state.")
        if source not in PANTRY_SOURCES:
            raise ValueError("Unsupported pantry source.")
        candidates.append(
            PantryCandidate(
                name=name,
                food_key=food_key,
                original_text=original_text,
                quantity_value=quantity_value,
                quantity_unit=quantity_unit,
                quantity_state=quantity_state,
                resolution_state=resolution_state,
                source=str(raw_item.get("source", source)).strip() or source,
                needs_review=needs_review,
            )
        )
    return tuple(candidates)


def pantry_candidate_to_display_text(candidate: PantryCandidate) -> str:
    if candidate.quantity_value is None or candidate.quantity_state != "known":
        return candidate.original_text
    quantity = f"{candidate.quantity_value:g}"
    if candidate.quantity_unit:
        return f"{quantity} {candidate.quantity_unit} {candidate.name}"
    return f"{quantity} {candidate.name}"


def pantry_candidates_to_legacy_items(
    candidates: tuple[PantryCandidate, ...] | list[PantryCandidate] | None,
) -> tuple[str, ...]:
    if not candidates:
        return ()
    return tuple(candidate.original_text for candidate in candidates)
