"""Load and validate the curated Carrinho meal catalogue."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re

from catalog import PLANNING_UNITS


MEAL_CATALOGUE_SCHEMA = "carrinho.meal-catalogue.v2"
_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
COOKING_ENERGY_VALUES = frozenset({"low", "normal", "high"})
DIETARY_TAG_VALUES = frozenset({"lactose-free"})
CATALOGUE_TIER_VALUES = frozenset({"core", "extended"})
SELECTION_TAG_VALUES = frozenset(
    {"batch-friendly", "leftover", "one-pan", "one-pot", "quick"}
)


@dataclass(frozen=True)
class MealIngredient:
    product_key: str
    quantity_per_person: float
    planning_unit: str


@dataclass(frozen=True)
class MealTemplate:
    key: str
    dish: str
    catalogue_tier: str
    cooking_energy: str
    dietary_tags: tuple[str, ...]
    selection_tags: tuple[str, ...]
    ingredients: tuple[MealIngredient, ...]


@dataclass(frozen=True)
class MealCatalogue:
    description: str
    templates: tuple[MealTemplate, ...]


def _required_text(data: dict[str, object], field: str, context: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} requires a non-empty {field}.")
    return value.strip()


def _validate_key(value: str, context: str) -> str:
    if not _KEY_PATTERN.fullmatch(value):
        raise ValueError(
            f"{context} must use lowercase letters, numbers, and underscores."
        )
    return value


def _validate_ingredient(data: object, position: int) -> MealIngredient:
    context = f"Ingredient {position}"
    if not isinstance(data, dict):
        raise ValueError(f"{context} must be an object.")

    product_key = _validate_key(
        _required_text(data, "product_key", context),
        f"{context} product_key",
    )
    planning_unit = _required_text(data, "planning_unit", context)
    if planning_unit not in PLANNING_UNITS:
        raise ValueError(f"{context} has an unsupported planning unit.")

    try:
        quantity_per_person = float(data.get("quantity_per_person"))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{context} has an invalid quantity per person.") from error
    if not math.isfinite(quantity_per_person) or quantity_per_person <= 0:
        raise ValueError(f"{context} has an invalid quantity per person.")

    return MealIngredient(
        product_key=product_key,
        quantity_per_person=quantity_per_person,
        planning_unit=planning_unit,
    )


def _validate_template(data: object, position: int) -> MealTemplate:
    context = f"Meal template {position}"
    if not isinstance(data, dict):
        raise ValueError(f"{context} must be an object.")

    key = _validate_key(_required_text(data, "key", context), f"{context} key")
    dish = _required_text(data, "dish", context)
    catalogue_tier = _required_text(data, "catalogue_tier", context)
    if catalogue_tier not in CATALOGUE_TIER_VALUES:
        raise ValueError(f"{context} has an unsupported catalogue tier.")

    cooking_energy = _required_text(data, "cooking_energy", context)
    if cooking_energy not in COOKING_ENERGY_VALUES:
        raise ValueError(f"{context} has an unsupported cooking energy value.")

    raw_dietary_tags = data.get("dietary_tags")
    if not isinstance(raw_dietary_tags, list) or not raw_dietary_tags:
        raise ValueError(f"{context} requires dietary tags.")
    dietary_tags = tuple(
        _required_text({"dietary_tag": tag}, "dietary_tag", context)
        for tag in raw_dietary_tags
    )
    if len(dietary_tags) != len(set(dietary_tags)):
        raise ValueError(f"{context} contains duplicate dietary tags.")
    unsupported_tags = sorted(set(dietary_tags).difference(DIETARY_TAG_VALUES))
    if unsupported_tags:
        raise ValueError(f"{context} has unsupported dietary tags.")

    raw_selection_tags = data.get("selection_tags")
    if not isinstance(raw_selection_tags, list) or not raw_selection_tags:
        raise ValueError(f"{context} requires selection tags.")
    selection_tags = tuple(
        _required_text({"selection_tag": tag}, "selection_tag", context)
        for tag in raw_selection_tags
    )
    if len(selection_tags) != len(set(selection_tags)):
        raise ValueError(f"{context} contains duplicate selection tags.")
    unsupported_selection_tags = sorted(
        set(selection_tags).difference(SELECTION_TAG_VALUES)
    )
    if unsupported_selection_tags:
        raise ValueError(f"{context} has unsupported selection tags.")

    raw_ingredients = data.get("ingredients")
    if not isinstance(raw_ingredients, list) or not raw_ingredients:
        raise ValueError(f"{context} requires at least one ingredient.")

    ingredients = tuple(
        _validate_ingredient(ingredient, ingredient_position)
        for ingredient_position, ingredient in enumerate(raw_ingredients, start=1)
    )
    product_keys = [ingredient.product_key for ingredient in ingredients]
    if len(product_keys) != len(set(product_keys)):
        raise ValueError(f"{context} contains duplicate product keys.")

    return MealTemplate(
        key=key,
        dish=dish,
        catalogue_tier=catalogue_tier,
        cooking_energy=cooking_energy,
        dietary_tags=dietary_tags,
        selection_tags=selection_tags,
        ingredients=ingredients,
    )


def parse_meal_catalogue_data(
    data: object,
    *,
    require_core: bool = True,
) -> MealCatalogue:
    """Validate one in-memory meal catalogue document."""
    if not isinstance(data, dict):
        raise ValueError("The meal catalogue must be a JSON object.")
    if data.get("schema") != MEAL_CATALOGUE_SCHEMA:
        raise ValueError("The meal catalogue has an unsupported schema.")

    description = _required_text(data, "description", "The meal catalogue")
    raw_templates = data.get("templates")
    if not isinstance(raw_templates, list) or not raw_templates:
        raise ValueError("The meal catalogue must contain meal templates.")

    templates = tuple(
        _validate_template(template, position)
        for position, template in enumerate(raw_templates, start=1)
    )
    template_keys = [template.key for template in templates]
    if len(template_keys) != len(set(template_keys)):
        raise ValueError("The meal catalogue contains duplicate template keys.")
    if require_core and not any(
        template.catalogue_tier == "core" for template in templates
    ):
        raise ValueError("The meal catalogue requires at least one core template.")

    return MealCatalogue(description=description, templates=templates)


def load_meal_catalogue(path: Path) -> MealCatalogue:
    """Load one versioned meal catalogue from JSON."""
    return parse_meal_catalogue_data(json.loads(path.read_text(encoding="utf-8")))


def load_default_meal_catalogue() -> MealCatalogue:
    """Load Carrinho's versioned, curated meal catalogue."""
    path = Path(__file__).resolve().parent / "data" / "meal-catalogue.json"
    return load_meal_catalogue(path)
