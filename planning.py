"""Build a predictable Carrinho meal plan without external services."""

from dataclasses import dataclass
import math
import re
import unicodedata

from catalog import PriceCatalog, Product, load_simulated_catalog
from meal_catalogue import MealTemplate, load_default_meal_catalogue
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
    meal_prep_guidance: tuple[str, ...]
    shopping_items: tuple[ShoppingItem, ...]
    pantry_usage: tuple[str, ...]
    budget: float
    people: int
    days: int
    currency: str
    price_type: str
    price_description: str

    @property
    def estimated_total(self) -> float:
        return round(sum(item.estimated_price for item in self.shopping_items), 2)

    @property
    def budget_balance(self) -> float:
        return round(self.budget - self.estimated_total, 2)


GRAMS_PER_POUND = 453.59237

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
) -> Plan:
    assert request.budget is not None
    assert request.people is not None
    assert request.days is not None

    meals_with_templates = _build_meals(request.days, templates)
    requirements = _calculate_requirements(
        meals_with_templates,
        request.people,
    )
    _validate_catalog_coverage(requirements, templates, catalog.products)

    return Plan(
        meals=tuple(meal for meal, _ in meals_with_templates),
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
) -> Plan | None:
    """Generate one meal plan and shopping list from a single price catalog."""
    selected_catalog = catalog or load_simulated_catalog()
    if not (
        request.budget is not None
        and request.currency == selected_catalog.currency
        and request.people is not None
        and 1 <= request.people <= 12
        and request.days is not None
        and 1 <= request.days <= 14
        and _restrictions_supported(request.dietary_restrictions)
    ):
        return None

    meal_catalogue = load_default_meal_catalogue()
    return _create_plan(request, meal_catalogue.templates, selected_catalog)
