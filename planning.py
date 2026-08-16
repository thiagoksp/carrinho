"""Build a predictable Carrinho meal plan without external services."""

from dataclasses import dataclass
import math
import re
import unicodedata

from catalog import PriceCatalog, Product
from local_catalogue import (
    load_effective_meal_catalogue,
    load_effective_price_catalog,
)
from meal_catalogue import MealCatalogue, MealTemplate
from request_parser import ParsedRequest


@dataclass(frozen=True)
class Meal:
    day: int
    meal_slot: str
    dish: str


@dataclass(frozen=True)
class ShoppingItem:
    name: str
    quantity_label: str
    estimated_price: float
    required_quantity: float
    purchase_quantity: float
    overage_quantity: float
    planning_unit: str
    package_count: int
    variable_weight: bool
    instacart_search_term: str
    instacart_quantity: float
    instacart_unit: str


@dataclass(frozen=True)
class Plan:
    meals: tuple[Meal, ...]
    meal_selection_guidance: tuple[str, ...]
    meal_prep_guidance: tuple[str, ...]
    shopping_items: tuple[ShoppingItem, ...]
    pantry_usage: tuple[str, ...]
    budget: float | None
    people: int
    days: int
    currency: str
    price_type: str
    price_description: str

    @property
    def estimated_total(self) -> float:
        return round(sum(item.estimated_price for item in self.shopping_items), 2)

    @property
    def budget_balance(self) -> float | None:
        if self.budget is None:
            return None
        return round(self.budget - self.estimated_total, 2)


GRAMS_PER_POUND = 453.59237
COOKING_ENERGY_RANKS = {"low": 1, "normal": 2, "high": 3}

NUMBER_WORD_VALUES = {
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
    "half": 0.5,
}


def _remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def _restrictions_supported(restrictions: list[str] | None) -> bool:
    if restrictions is None:
        return False
    return all(
        "lactose" in _remove_accents(restriction)
        for restriction in restrictions
    )


def _build_meals(
    days: int,
    templates: tuple[MealTemplate, ...],
) -> tuple[tuple[Meal, MealTemplate], ...]:
    meals: list[tuple[Meal, MealTemplate]] = []
    meal_slots = ("Lunch", "Dinner")

    for day in range(1, days + 1):
        for meal_slot_index, meal_slot in enumerate(meal_slots):
            index = ((day - 1) * 2 + meal_slot_index) % len(templates)
            template = templates[index]
            meals.append((Meal(day, meal_slot, template.dish), template))

    return tuple(meals)


def _required_dietary_tags(restrictions: list[str] | None) -> frozenset[str]:
    if not restrictions:
        return frozenset()
    if any("lactose" in _remove_accents(restriction) for restriction in restrictions):
        return frozenset({"lactose-free"})
    return frozenset()


def validate_meal_candidate_keys(
    candidate_keys: list[str] | tuple[str, ...],
    request: ParsedRequest,
    meal_catalogue: MealCatalogue | None = None,
) -> tuple[MealTemplate, ...]:
    """Validate an ordered future-LLM candidate list against local hard rules."""
    if not isinstance(candidate_keys, (list, tuple)) or any(
        not isinstance(key, str) or not key.strip() for key in candidate_keys
    ):
        raise ValueError("Meal candidate keys must be a list of non-empty strings.")
    if not candidate_keys:
        raise ValueError("Meal candidate keys must not be empty.")
    if not _restrictions_supported(request.dietary_restrictions):
        raise ValueError("Meal candidates cannot use unsupported dietary restrictions.")
    normalized_keys = tuple(key.strip() for key in candidate_keys)
    if len(normalized_keys) != len(set(normalized_keys)):
        raise ValueError("Meal candidate keys must not contain duplicates.")

    selected_catalogue = meal_catalogue or load_effective_meal_catalogue()
    templates_by_key = {
        template.key: template for template in selected_catalogue.templates
    }
    unknown_keys = [key for key in normalized_keys if key not in templates_by_key]
    if unknown_keys:
        raise ValueError("Unknown meal candidate key: " + ", ".join(unknown_keys) + ".")

    required_tags = _required_dietary_tags(request.dietary_restrictions)
    selected_templates = tuple(templates_by_key[key] for key in normalized_keys)
    if any(
        not required_tags.issubset(template.dietary_tags)
        for template in selected_templates
    ):
        raise ValueError("A meal candidate does not satisfy the dietary restrictions.")
    return selected_templates


def _validate_preference_keys(
    request: ParsedRequest,
    products: tuple[Product, ...],
) -> None:
    avoided_keys = tuple(request.avoided_product_keys or ())
    preferred_keys = tuple(request.preferred_product_keys or ())
    available_keys = {product.key for product in products}
    unknown_keys = set(avoided_keys + preferred_keys).difference(available_keys)
    if unknown_keys:
        raise ValueError("Unknown food preference key: " + ", ".join(sorted(unknown_keys)) + ".")
    if len(avoided_keys) != len(set(avoided_keys)) or len(preferred_keys) != len(
        set(preferred_keys)
    ):
        raise ValueError("Food preference keys must not contain duplicates.")
    if set(avoided_keys).intersection(preferred_keys):
        raise ValueError("The same food cannot be both avoided and preferred.")


def _template_pantry_coverage(
    template: MealTemplate,
    pantry_items: list[str] | None,
    products_by_key: dict[str, Product],
) -> int:
    return sum(
        1
        for ingredient in template.ingredients
        if ingredient.product_key in products_by_key
        and any(
            _item_matches(item, products_by_key[ingredient.product_key])
            for item in (pantry_items or [])
        )
    )


def _select_templates(
    request: ParsedRequest,
    templates: tuple[MealTemplate, ...],
    products: tuple[Product, ...],
) -> tuple[MealTemplate, ...]:
    required_tags = _required_dietary_tags(request.dietary_restrictions)
    eligible_templates = tuple(
        template
        for template in templates
        if required_tags.issubset(template.dietary_tags)
    )
    if not eligible_templates:
        raise ValueError("The meal catalogue has no templates for these restrictions.")

    required_meal_count = (request.days or 0) * 2
    products_by_key = {product.key: product for product in products}
    request_energy = request.cooking_energy or "normal"
    avoided_keys = frozenset(request.avoided_product_keys or ())
    preferred_keys = frozenset(request.preferred_product_keys or ())

    def rank(candidates: tuple[MealTemplate, ...]) -> tuple[MealTemplate, ...]:
        return tuple(
            template
            for _, template in sorted(
                enumerate(candidates),
                key=lambda indexed_template: (
                    len(
                        avoided_keys.intersection(
                            ingredient.product_key
                            for ingredient in indexed_template[1].ingredients
                        )
                    ),
                    abs(
                        COOKING_ENERGY_RANKS[indexed_template[1].cooking_energy]
                        - COOKING_ENERGY_RANKS[request_energy]
                    ),
                    -len(
                        preferred_keys.intersection(
                            ingredient.product_key
                            for ingredient in indexed_template[1].ingredients
                        )
                    ),
                    -_template_pantry_coverage(
                        indexed_template[1],
                        request.pantry_items,
                        products_by_key,
                    ),
                    indexed_template[0],
                ),
            )
        )

    core_templates = tuple(
        template
        for template in eligible_templates
        if template.catalogue_tier == "core"
    )
    extended_templates = tuple(
        template
        for template in eligible_templates
        if template.catalogue_tier == "extended"
    )
    if core_templates and required_meal_count >= len(core_templates):
        if avoided_keys or preferred_keys:
            return rank(core_templates) + rank(extended_templates)
        return core_templates + rank(extended_templates)
    return rank(eligible_templates)


def select_meal_candidate_templates(
    request: ParsedRequest,
    catalog: PriceCatalog | None = None,
    meal_catalogue: MealCatalogue | None = None,
) -> tuple[MealTemplate, ...]:
    """Return locally eligible meal templates in deterministic fallback order."""
    selected_catalog = catalog or load_effective_price_catalog()
    selected_meals = meal_catalogue or load_effective_meal_catalogue()
    _validate_preference_keys(request, selected_catalog.products)
    return _select_templates(
        request,
        selected_meals.templates,
        selected_catalog.products,
    )


def _describe_meal_selection(
    request: ParsedRequest,
    selected_templates: tuple[MealTemplate, ...],
) -> tuple[str, ...]:
    required_meal_count = (request.days or 0) * 2
    guidance = [
        "Selection is deterministic: cooking energy, then pantry coverage."
    ]
    if _required_dietary_tags(request.dietary_restrictions):
        guidance.append("Dietary filter applied: lactose-free meal templates.")
    if request.avoided_product_keys or request.preferred_product_keys:
        guidance.append(
            "Soft food preferences influenced meal ranking after dietary filters."
        )
    core_template_count = sum(
        template.catalogue_tier == "core" for template in selected_templates
    )
    if core_template_count and required_meal_count >= core_template_count:
        guidance.append(
            "The plan uses the complete core library, so core catalogue order is preserved."
        )
    else:
        guidance.append(
            f"Cooking energy preference applied: {request.cooking_energy or 'normal'}."
        )
    return tuple(guidance)


def _calculate_requirements(
    meals: tuple[tuple[Meal, MealTemplate], ...], people: int
) -> dict[str, float]:
    requirements: dict[str, float] = {}
    for _, template in meals:
        for ingredient in template.ingredients:
            requirements[ingredient.product_key] = requirements.get(
                ingredient.product_key,
                0,
            ) + (
                ingredient.quantity_per_person * people
            )
    return requirements


def _item_matches(item: str, product: Product) -> bool:
    normalized_item = _remove_accents(item)
    return any(keyword in normalized_item for keyword in product.keywords)


def _extract_number(text: str) -> float | None:
    fraction = re.search(r"\b(\d+)\s*/\s*(\d+)\b", text)
    if fraction and int(fraction.group(2)) != 0:
        return int(fraction.group(1)) / int(fraction.group(2))

    number = re.search(r"\b\d+(?:[.,]\d+)?\b", text)
    if number:
        return float(number.group().replace(",", "."))

    for word, value in NUMBER_WORD_VALUES.items():
        if re.search(rf"\b{word}\b", text):
            return value
    return None


def _item_quantity(item: str, product: Product) -> float | None:
    text = _remove_accents(item)
    number = _extract_number(text)
    if number is None:
        return None

    if product.planning_unit == "each":
        if re.search(r"\bdozens?\b", text):
            return number * 12
        return number

    if product.planning_unit == "can":
        if re.search(r"\bcans?\b", text):
            return number
        if re.search(r"\b(?:packages?|packs?)\b", text):
            return number * product.package_size
        return None

    if product.planning_unit == "ml":
        if re.search(r"\b(?:ml|millilitres?|milliliters?)\b", text):
            return number
        if re.search(r"\b(?:l|litres?|liters?)\b", text):
            return number * 1000
        if re.search(r"\bbottles?\b", text):
            return number * product.package_size
        return None

    if product.planning_unit == "package":
        if re.search(r"\b(?:packages?|packs?|jars?)\b", text):
            return number * product.package_size
        return None

    if re.search(r"\b(?:kg|kilograms?|kilogrammes?)\b", text):
        return number * 1000
    if re.search(r"\b(?:g|grams?)\b", text):
        return number
    if re.search(r"\b(?:lb|lbs|pounds?)\b", text):
        return number * GRAMS_PER_POUND
    if re.search(r"\b(?:packages?|packs?|bags?|units?|items?)\b", text):
        return number * product.package_size
    return None


def _available_quantity(
    product: Product, pantry_items: list[str] | None
) -> float:
    matching_items = [
        item
        for item in (pantry_items or [])
        if _item_matches(item, product)
    ]
    if not matching_items:
        return 0

    quantities = [_item_quantity(item, product) for item in matching_items]
    if any(quantity is None for quantity in quantities):
        return math.inf
    return sum(quantity or 0 for quantity in quantities)


def _build_shopping_items(
    requirements: dict[str, float],
    pantry_items: list[str] | None,
    products: tuple[Product, ...],
) -> tuple[ShoppingItem, ...]:
    shopping_items: list[ShoppingItem] = []
    for product in products:
        required_amount = requirements.get(product.key, 0)
        available_amount = _available_quantity(product, pantry_items)
        shortfall = max(0, required_amount - available_amount)
        if shortfall <= 0:
            continue

        packages_needed = math.ceil(shortfall / product.package_size)
        quantity_label = f"{packages_needed} x {product.package_description}"
        shopping_items.append(
            ShoppingItem(
                name=product.name,
                quantity_label=quantity_label,
                estimated_price=round(
                    packages_needed * product.package_price,
                    2,
                ),
                required_quantity=round(shortfall, 6),
                purchase_quantity=round(
                    packages_needed * product.package_size,
                    6,
                ),
                overage_quantity=round(
                    max(
                        0,
                        packages_needed * product.package_size - shortfall,
                    ),
                    6,
                ),
                planning_unit=product.planning_unit,
                package_count=packages_needed,
                variable_weight=product.variable_weight,
                instacart_search_term=product.instacart_search_term,
                instacart_quantity=round(
                    packages_needed * product.instacart_quantity,
                    6,
                ),
                instacart_unit=product.instacart_unit,
            )
        )
    return tuple(shopping_items)


def _validate_catalog_coverage(
    requirements: dict[str, float],
    templates: tuple[MealTemplate, ...],
    products: tuple[Product, ...],
) -> None:
    products_by_key = {product.key: product for product in products}
    available_keys = set(products_by_key)
    meal_catalogue_keys = {
        ingredient.product_key
        for template in templates
        for ingredient in template.ingredients
    }
    missing_keys = sorted(meal_catalogue_keys.difference(available_keys))
    if missing_keys:
        raise ValueError(
            "The catalog does not contain prices for: "
            + ", ".join(missing_keys)
            + "."
        )

    incompatible_units = sorted(
        {
            f"{template.key}:{ingredient.product_key}"
            for template in templates
            for ingredient in template.ingredients
            if (
                ingredient.product_key in products_by_key
                and ingredient.planning_unit
                != products_by_key[ingredient.product_key].planning_unit
            )
        }
    )
    if incompatible_units:
        raise ValueError(
            "The meal catalogue has incompatible planning units for: "
            + ", ".join(incompatible_units)
            + "."
        )


def _describe_pantry_usage(
    requirements: dict[str, float],
    pantry_items: list[str] | None,
    products: tuple[Product, ...],
) -> tuple[str, ...]:
    usage_notes: list[str] = []
    for product in products:
        required_amount = requirements.get(product.key, 0)
        available_amount = _available_quantity(product, pantry_items)
        if required_amount <= 0 or available_amount <= 0:
            continue

        if not math.isinf(available_amount):
            used_amount = min(required_amount, available_amount)
            quantity = format_planning_quantity(
                used_amount,
                product.planning_unit,
                product.name,
            )
            usage_notes.append(
                f"{product.name}: the plan will use "
                f"{quantity} from the pantry."
            )
        else:
            usage_notes.append(
                f"{product.name}: the plan will use what is already at home."
            )
    return tuple(usage_notes)


def format_planning_quantity(
    quantity: float,
    unit: str,
    product_name: str | None = None,
) -> str:
    """Format a canonical planning quantity for a Canadian reader."""
    def compact(value: float, decimal_places: int) -> str:
        return f"{value:.{decimal_places}f}".rstrip("0").rstrip(".")

    if unit == "g":
        if quantity >= 1000:
            return f"{compact(quantity / 1000, 3)} kg"
        return f"{compact(quantity, 1)} g"
    if unit == "ml":
        if quantity >= 1000:
            return f"{compact(quantity / 1000, 3)} L"
        return f"{compact(quantity, 1)} ml"
    labels = {
        "can": ("can", "cans"),
        "each": ("item", "items"),
        "package": ("package", "packages"),
    }
    singular, plural = labels[unit]
    if unit == "each" and product_name and "egg" in product_name.casefold():
        singular, plural = "egg", "eggs"
    label = singular if math.isclose(quantity, 1.0) else plural
    return f"{compact(quantity, 3)} {label}"


def _create_plan(
    request: ParsedRequest,
    templates: tuple[MealTemplate, ...],
    catalog: PriceCatalog,
    meal_candidate_keys: list[str] | tuple[str, ...] | None = None,
) -> Plan:
    assert request.people is not None
    assert request.days is not None

    if meal_candidate_keys is None:
        selected_templates = _select_templates(request, templates, catalog.products)
        llm_selected = False
    else:
        selected_templates = validate_meal_candidate_keys(
            meal_candidate_keys,
            request,
            MealCatalogue(description="Selected meal candidates", templates=templates),
        )
        llm_selected = True
    meals_with_templates = _build_meals(request.days, selected_templates)
    requirements = _calculate_requirements(
        meals_with_templates,
        request.people,
    )
    _validate_catalog_coverage(requirements, selected_templates, catalog.products)

    return Plan(
        meals=tuple(meal for meal, _ in meals_with_templates),
        meal_selection_guidance=_describe_meal_selection(
            request,
            selected_templates,
        )
        + (
            (
                "Optional LLM meal order was validated against known local templates.",
            )
            if llm_selected
            else ()
        ),
        meal_prep_guidance=(
            "Prepare extra portions when the next meal uses food made earlier.",
            "Cook enough rice for up to two days and refrigerate leftovers promptly.",
            "Set aside future portions before serving to simplify meal preparation.",
        ),
        shopping_items=_build_shopping_items(
            requirements,
            request.pantry_items,
            catalog.products,
        ),
        pantry_usage=_describe_pantry_usage(
            requirements,
            request.pantry_items,
            catalog.products,
        ),
        budget=request.budget,
        people=request.people,
        days=request.days,
        currency=catalog.currency,
        price_type=catalog.price_type,
        price_description=catalog.description,
    )


def generate_plan(
    request: ParsedRequest,
    catalog: PriceCatalog | None = None,
    meal_catalogue: MealCatalogue | None = None,
    meal_candidate_keys: list[str] | tuple[str, ...] | None = None,
) -> Plan | None:
    """Generate one meal plan and shopping list from a single price catalog."""
    selected_catalog = catalog or load_effective_price_catalog()
    if not (
        (request.currency in {None, selected_catalog.currency})
        and request.people is not None
        and 1 <= request.people <= 12
        and request.days is not None
        and 1 <= request.days <= 14
        and _restrictions_supported(request.dietary_restrictions)
    ):
        return None

    _validate_preference_keys(request, selected_catalog.products)

    selected_meals = meal_catalogue or load_effective_meal_catalogue()
    return _create_plan(
        request,
        selected_meals.templates,
        selected_catalog,
        meal_candidate_keys,
    )
