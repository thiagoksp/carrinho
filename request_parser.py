"""Parse grocery requests written in everyday language."""

from dataclasses import dataclass
import re
import unicodedata

from catalog import resolve_product_keys
from local_catalogue import load_effective_price_catalog


@dataclass
class ParsedRequest:
    """Data that Carrinho identified in the user's request."""

    budget: float | None = None
    currency: str | None = None
    people: int | None = None
    days: int | None = None
    cooking_energy: str | None = None
    pantry_items: list[str] | None = None
    dietary_restrictions: list[str] | None = None
    avoided_product_keys: list[str] | None = None
    preferred_product_keys: list[str] | None = None


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

NUMBER_PATTERN = r"\d+|one|two|three|four|five|six|seven|eight|nine|ten"


def _remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def _parse_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS[_remove_accents(value)]


def _find_budget(text: str) -> tuple[float | None, str | None]:
    match = re.search(
        r"(?P<currency>CAD|USD|BRL|CA\$|US\$|R\$|\$)\s*\$?\s*"
        r"(?P<value>\d+(?:[.,]\d{1,2})?)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None, None

    original_currency = match.group("currency").upper()
    currency_aliases = {
        "CA$": "CAD",
        "US$": "USD",
        "R$": "BRL",
        "$": "CAD",
    }
    currency = currency_aliases.get(original_currency, original_currency)
    value = float(match.group("value").replace(",", "."))
    return value, currency


def _find_quantity(text: str, unit: str) -> int | None:
    match = re.search(
        rf"\b(?P<number>{NUMBER_PATTERN})\s+(?:{unit})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    return _parse_number(match.group("number"))


def _find_cooking_energy(text: str) -> str | None:
    normalized_text = _remove_accents(text)
    low_energy_phrases = (
        "low cooking energy",
        "low energy for cooking",
        "little energy for cooking",
        "no energy for cooking",
        "do not want to cook",
        "don't want to cook",
    )
    high_energy_phrases = (
        "high cooking energy",
        "high energy for cooking",
        "lots of energy for cooking",
    )

    if any(phrase in normalized_text for phrase in low_energy_phrases):
        return "low"
    if any(phrase in normalized_text for phrase in high_energy_phrases):
        return "high"
    if "normal cooking energy" in normalized_text:
        return "normal"
    return None


def _find_pantry_items(text: str) -> list[str] | None:
    normalized_text = _remove_accents(text)
    no_item_phrases = (
        "i have nothing at home",
        "we have nothing at home",
        "no items at home",
        "my pantry is empty",
        "our pantry is empty",
    )
    if any(phrase in normalized_text for phrase in no_item_phrases):
        return []

    match = re.search(
        r"(?:(?:i|we)\s+already\s+have|already\s+have|"
        r"(?:i|we)\s+have\s+at\s+home)\s+"
        r"(?P<items>.+?)"
        r"(?=,\s*(?:and\s+)?(?:at\s+least|someone|one\s+person|"
        r"i\s+live|we\s+live|i\s+am|we\s+are|i\s+prefer|we\s+prefer|"
        r"we\s+need|i\s+need|store\s+preference|preferred\s+store)"
        r"|\s+and\s+(?:i\s+live|we\s+live|i\s+am|we\s+are|"
        r"i\s+prefer|we\s+prefer|we\s+need|i\s+need)|[.;]|$)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    items = re.split(r"\s*,\s*|\s+and\s+", match.group("items"))
    return [item.strip().casefold() for item in items if item.strip()]


def _find_dietary_restrictions(text: str) -> list[str] | None:
    normalized_text = _remove_accents(text)
    no_restriction_phrases = (
        "no dietary restriction",
        "no dietary restrictions",
        "without dietary restrictions",
        "do not have any dietary restrictions",
        "don't have any dietary restrictions",
    )
    if any(phrase in normalized_text for phrase in no_restriction_phrases):
        return []

    known_restrictions = (
        ("lactose intolerance", ("lactose", "dairy free", "milk free")),
        ("vegetarian", ("vegetarian",)),
        ("vegan", ("vegan",)),
        ("avoid gluten ingredients", ("avoid gluten", "gluten free", "no gluten", "no gluten ingredients")),
    )
    found: list[str] = []
    for restriction, phrases in known_restrictions:
        if any(phrase in normalized_text for phrase in phrases):
            found.append(restriction)
    return found or None


def _find_product_preferences(text: str, preference: str) -> list[str] | None:
    normalized_text = _remove_accents(text)
    no_preference_phrases = {
        "avoid": (
            "no foods to avoid",
            "no food to avoid",
            "do not avoid any foods",
            "don't avoid any foods",
        ),
        "prefer": (
            "no food preferences",
            "no preferred foods",
            "do not prefer any foods",
            "don't prefer any foods",
        ),
    }
    if any(phrase in normalized_text for phrase in no_preference_phrases[preference]):
        return []

    patterns = {
        "avoid": (
            r"(?:i|we)\s+(?:do\s+not|don't)\s+like\s+(?P<items>[^.;]+)",
            r"(?:i|we)\s+(?:dislike|avoid)\s+(?P<items>[^.;]+)",
        ),
        "prefer": (
            r"(?:my|our)\s+favou?rite\s+foods?\s+(?:is|are)\s+(?P<items>[^.;]+)",
            r"(?:i|we)\s+(?:like|prefer)(?:\s+eating)?\s+(?P<items>[^.;]+)",
        ),
    }
    for pattern in patterns[preference]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match is None:
            continue
        food_names = re.split(r"\s*,\s*|\s+and\s+", match.group("items"))
        food_names = [name.strip() for name in food_names if name.strip()]
        try:
            product_keys = resolve_product_keys(
                food_names,
                load_effective_price_catalog().products,
            )
        except ValueError:
            return None
        return list(product_keys)
    return None


def parse_request(text: str) -> ParsedRequest:
    """Extract data that is explicitly present in a grocery request."""
    budget, currency = _find_budget(text)

    return ParsedRequest(
        budget=budget,
        currency=currency,
        people=_find_quantity(text, r"people|persons?"),
        days=_find_quantity(text, r"days?"),
        cooking_energy=_find_cooking_energy(text),
        pantry_items=_find_pantry_items(text),
        dietary_restrictions=_find_dietary_restrictions(text),
        avoided_product_keys=_find_product_preferences(text, "avoid"),
        preferred_product_keys=_find_product_preferences(text, "prefer"),
    )
