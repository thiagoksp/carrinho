"""Build retailer-neutral previews for an Instacart shopping-list handoff."""

import json
import math
from pathlib import Path
import unicodedata

from catalog import INSTACART_UNITS
from planning import Plan, ShoppingItem


PASTE_ITEM_LIMIT = 200


def _require_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"The item must include {field_name}.")
    return text


def _json_number(value: float) -> int | float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("The Instacart quantity must be finite and greater than zero.")
    if value.is_integer():
        return int(value)
    return value


def _convert_item(item: ShoppingItem) -> dict[str, object]:
    unit = _require_text(item.instacart_unit, "a unit")
    if unit not in INSTACART_UNITS:
        raise ValueError(f"Unsupported Instacart unit: {unit}.")

    name = _require_text(item.instacart_search_term, "a search term")
    display_text = _require_text(
        f"{item.name}: {item.quantity_label}",
        "display text",
    )
    quantity = _json_number(float(item.instacart_quantity))
    return {
        "name": name,
        "display_text": display_text,
        "line_item_measurements": [
            {
                "quantity": quantity,
                "unit": unit,
            }
        ],
    }


def create_instacart_payload(plan: Plan) -> dict[str, object]:
    """Convert a plan without making network calls or including prices."""
    if not plan.shopping_items:
        raise ValueError("There are no shopping items for the Instacart list.")

    people_label = "person" if plan.people == 1 else "people"
    day_label = "day" if plan.days == 1 else "days"
    return {
        "title": (
            f"Carrinho list — {plan.people} {people_label} "
            f"for {plan.days} {day_label}"
        ),
        "link_type": "shopping_list",
        "line_items": [_convert_item(item) for item in plan.shopping_items],
    }


def serialize_instacart_payload(plan: Plan) -> str:
    """Serialize a local preview as valid, readable JSON."""
    return json.dumps(
        create_instacart_payload(plan),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )


def _format_paste_measurement(item: ShoppingItem) -> str:
    quantity = _json_number(float(item.instacart_quantity))
    unit = _require_text(item.instacart_unit, "a unit")

    if unit == "each":
        return str(quantity)
    if unit == "can":
        label = "can" if quantity == 1 else "cans"
        return f"{quantity} {label}"
    if unit == "package":
        label = "package" if quantity == 1 else "packages"
        return f"{quantity} {label}"
    if unit in INSTACART_UNITS:
        return f"{quantity} {unit}"
    raise ValueError(f"Unsupported Instacart unit: {unit}.")


def _safe_paste_term(value: str) -> str:
    name = _require_text(value, "a search term")
    separators = {",", "\r", "\n", "\u2028", "\u2029"}
    if any(
        character in separators
        or unicodedata.category(character).startswith("C")
        for character in name
    ):
        raise ValueError("The search term cannot contain separators or control characters.")
    return name


def create_instacart_paste_list(plan: Plan) -> str:
    """Create local text with one product per line for manual pasting."""
    if not plan.shopping_items:
        raise ValueError("There are no shopping items for the Instacart list.")
    if len(plan.shopping_items) > PASTE_ITEM_LIMIT:
        raise ValueError(
            f"The paste list accepts no more than {PASTE_ITEM_LIMIT} items."
        )

    lines = []
    for item in plan.shopping_items:
        name = _safe_paste_term(item.instacart_search_term)
        measurement = _format_paste_measurement(item)
        lines.append(f"{name} ({measurement})")

    paste_list = "\n".join(lines)
    if len(paste_list.splitlines()) != len(plan.shopping_items):
        raise ValueError("The paste list contains unexpected separators.")
    return paste_list


def _next_available_path(
    directory: Path,
    base_name: str,
    extension: str,
) -> Path:
    path = directory / f"{base_name}.{extension}"
    number = 2
    while path.exists():
        path = directory / f"{base_name}-{number}.{extension}"
        number += 1
    return path


def save_instacart_payload(
    plan: Plan,
    output_directory: Path | None = None,
) -> Path:
    """Save a new JSON preview without replacing an earlier file."""
    directory = output_directory or Path(__file__).resolve().parent / "outputs"
    directory.mkdir(parents=True, exist_ok=True)
    path = _next_available_path(directory, "instacart-list", "json")
    path.write_text(
        f"{serialize_instacart_payload(plan)}\n",
        encoding="utf-8",
    )
    return path


def save_instacart_paste_list(
    plan: Plan,
    output_directory: Path | None = None,
) -> Path:
    """Save text that the user can paste manually into a Shopping List."""
    directory = output_directory or Path(__file__).resolve().parent / "outputs"
    directory.mkdir(parents=True, exist_ok=True)
    path = _next_available_path(directory, "instacart-paste-list", "txt")
    path.write_text(
        f"{create_instacart_paste_list(plan)}\n",
        encoding="utf-8",
    )
    return path
