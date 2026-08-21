"""Build a predictable Carrinho meal plan without external services."""

from dataclasses import dataclass
import math
import re
import unicodedata

from catalog import PriceCatalog, Product
from pantry import PantryCandidate, parse_pantry_candidates
from food_rules import (
    build_food_rules_for_avoided_products,
    build_food_rules_for_dietary_restrictions,
    normalize_food_rule_values,
    restriction_to_tag,
)
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
    instructions: tuple[str, ...] = ()
    difficulty: str = "easy"


@dataclass(frozen=True)
class ShoppingItem:
    name: str
    quantity_label: str
    estimated_price: float
    estimated_price_min: float
    estimated_price_max: float
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
    meal_templates: tuple["MealTemplate", ...]
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
    def estimated_total_min(self) -> float:
        return round(sum(item.estimated_price_min for item in self.shopping_items), 2)

    @property
    def estimated_total_max(self) -> float:
        return round(sum(item.estimated_price_max for item in self.shopping_items), 2)

    @property
    def budget_balance(self) -> float | None:
        if self.budget is None:
            return None
        return round(self.budget - self.estimated_total, 2)

    @property
    def budget_balance_min(self) -> float | None:
        if self.budget is None:
            return None
        return round(self.budget - self.estimated_total_max, 2)

    @property
    def budget_balance_max(self) -> float | None:
        if self.budget is None:
            return None
        return round(self.budget - self.estimated_total_min, 2)


GRAMS_PER_POUND = 453.59237
ESTIMATE_VARIATION_LOW = 0.85
ESTIMATE_VARIATION_HIGH = 1.20
COOKING_ENERGY_RANKS = {"low": 1, "normal": 2, "high": 3}
BUDGET_CATEGORY_STANDARD = "standard"
BUDGET_CATEGORY_LOW = "low"
INSTANT_NOODLE_FLOOR_KEY = "instant_noodles"
INSTANT_NOODLE_FLOOR_PRICE = 0.99
DEFAULT_TEMPLATE_EXCLUSION_KEYS = frozenset(
    {
        "coconut_milk",
        "chickpeas",
        "lentils",
        "corn_tortillas",
        "canned_corn",
        "curry_blend",
    }
)


class BudgetInfeasibleError(ValueError):
    """Raised when no validated meal sequence fits the requested budget."""

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
    """Accept the known deterministic household dietary presets only."""
    if restrictions is None:
        return True
    try:
        normalize_food_rule_values(restrictions)
    except ValueError:
        return False
    return True


def _default_meal_instructions(template: MealTemplate) -> tuple[str, ...]:
    dish = template.dish.casefold()
    if "omelette" in dish:
        return (
            "Warm oil in a skillet, then cook the potatoes and onions until tender.",
            "Beat the eggs, pour them in, and fold until just set.",
            "Add vegetables and serve with a little seasoning.",
        )
    if "pasta" in dish and "beef" in dish:
        return (
            "Boil the pasta until just tender.",
            "Brown the beef with onions and garlic, then stir in tomato sauce.",
            "Combine the pasta and sauce, finish with seasoning, and serve.",
        )
    if "bean" in dish and "stew" in dish:
        return (
            "Sauté onions and garlic in oil until fragrant.",
            "Add beans, tomato sauce, and a splash of water for a quick stew.",
            "Simmer until thick, then serve over rice.",
        )
    if "rice" in dish and "egg" in dish:
        return (
            "Warm the rice and oil in a skillet.",
            "Scramble the eggs with onion and vegetables until cooked.",
            "Fold everything together and finish with seasoning.",
        )
    if "chicken" in dish and "rice" in dish:
        return (
            "Cook the rice and roast or pan-sear the chicken until browned.",
            "Sauté the vegetables and onion with oil and seasoning.",
            "Serve the chicken and vegetables over the rice.",
        )
    if "bean" in dish or "beef" in dish or "potato" in dish:
        return (
            "Cook the main protein with onions and garlic until browned.",
            "Add the vegetables or potato, then season well.",
            "Serve hot with rice or as a skillet meal.",
        )
    if "rice" in dish:
        return (
            "Cook the rice until tender.",
            "Sauté the vegetables and aromatics with oil and seasoning.",
            "Combine and serve warm.",
        )
    return (
        "Cook the main ingredients in a single pan or pot.",
        "Add seasoning and vegetables to finish the dish.",
        "Serve warm and keep leftovers for the next meal.",
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
            instructions = template.instructions or _default_meal_instructions(template)
            meals.append(
                (
                    Meal(
                        day,
                        meal_slot,
                        template.dish,
                        instructions,
                        template.difficulty,
                    ),
                    template,
                )
            )

    return tuple(meals)


def _required_dietary_tags(restrictions: list[str] | None) -> frozenset[str]:
    if not restrictions:
        return frozenset()
    required_tags: set[str] = set()
    for restriction in restrictions:
        normalized = _remove_accents(str(restriction)).replace("_", " ").replace("-", " ")
        if "lactose" in normalized:
            required_tags.add("lactose-free")
        elif "vegetarian" in normalized:
            required_tags.add("vegetarian")
        elif "vegan" in normalized:
            required_tags.add("vegan")
            required_tags.add("vegetarian")
        elif "gluten" in normalized or "no gluten" in normalized:
            required_tags.add("no-gluten-ingredients")
    return frozenset(required_tags)


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


def _template_estimated_cost(
    template: MealTemplate,
    people: int,
    products_by_key: dict[str, Product],
) -> float:
    """Estimate package cost for one meal without changing final calculations."""
    return round(
        sum(
            math.ceil(
                ingredient.quantity_per_person * people
                / products_by_key[ingredient.product_key].package_size
            )
            * products_by_key[ingredient.product_key].package_price
            for ingredient in template.ingredients
        ),
        2,
    )


def _selection_purchase_cost(
    templates: tuple[MealTemplate, ...],
    request: ParsedRequest,
    products: tuple[Product, ...],
) -> float:
    if not templates or request.days is None or request.people is None:
        return 0
    meals = _build_meals(request.days, templates)
    requirements = _calculate_requirements(meals, request.people)
    shopping_items = _build_shopping_items(
        requirements,
        request.pantry_items,
        products,
    )
    return round(sum(item.estimated_price for item in shopping_items), 2)


def _sequence_purchase_cost(
    templates: tuple[MealTemplate, ...],
    request: ParsedRequest,
    products: tuple[Product, ...],
) -> float:
    if not templates or request.days is None or request.people is None:
        return 0
    meal_count = request.days * 2
    requirements: dict[str, float] = {}
    for index in range(meal_count):
        template = templates[index % len(templates)]
        for ingredient in template.ingredients:
            requirements[ingredient.product_key] = requirements.get(
                ingredient.product_key,
                0,
            ) + ingredient.quantity_per_person * request.people
    shopping_items = _build_shopping_items(
        requirements,
        request.pantry_items,
        products,
    )
    return round(sum(item.estimated_price for item in shopping_items), 2)


def _budget_category(request: ParsedRequest) -> str:
    """Classify budget pressure without exposing a user-selectable category."""
    if request.budget is None or request.people is None or request.days is None:
        return BUDGET_CATEGORY_STANDARD
    meal_count = request.people * request.days * 2
    per_meal_budget = request.budget / meal_count
    if per_meal_budget < INSTANT_NOODLE_FLOOR_PRICE:
        return BUDGET_CATEGORY_LOW
    if per_meal_budget <= INSTANT_NOODLE_FLOOR_PRICE * 1.5:
        return BUDGET_CATEGORY_LOW
    return BUDGET_CATEGORY_STANDARD


def _budget_floor(request: ParsedRequest) -> float | None:
    if request.people is None or request.days is None:
        return None
    return round(
        INSTANT_NOODLE_FLOOR_PRICE * request.people * request.days * 2,
        2,
    )


def _select_budget_sequence(
    request: ParsedRequest,
    candidates: tuple[MealTemplate, ...],
    products: tuple[Product, ...],
) -> tuple[MealTemplate, ...]:
    if request.budget is None or request.days is None:
        return candidates

    meal_count = request.days * 2
    products_by_key = {product.key: product for product in products}
    ranked_candidates = tuple(
        sorted(
            candidates,
            key=lambda template: _template_estimated_cost(
                template,
                request.people or 1,
                products_by_key,
            ),
        )
    )
    states: list[tuple[MealTemplate, ...]] = [()]
    best_states: list[tuple[MealTemplate, ...]] = []
    for _ in range(min(meal_count, 8)):
        next_states: list[tuple[MealTemplate, ...]] = []
        for state in states:
            for candidate in ranked_candidates:
                sequence = state + (candidate,)
                if _sequence_purchase_cost(sequence, request, products) <= request.budget:
                    next_states.append(sequence)
        if not next_states:
            break
        next_states.sort(
            key=lambda sequence: (
                _sequence_purchase_cost(sequence, request, products),
                len({template.key for template in sequence}),
                -len(sequence),
            ),
            reverse=True,
        )
        best_states.extend(next_states[:80])
        states = next_states[:80]

    if not best_states:
        floor = _budget_floor(request)
        floor_text = f" The minimum reference floor is CAD${floor:.2f}." if floor else ""
        raise BudgetInfeasibleError(
            "No validated meal plan fits the requested budget." + floor_text
        )
    return max(
        best_states,
        key=lambda sequence: (
            _sequence_purchase_cost(sequence, request, products),
            len({template.key for template in sequence}),
            -len(sequence),
        ),
    )


def _select_templates(
    request: ParsedRequest,
    templates: tuple[MealTemplate, ...],
    products: tuple[Product, ...],
) -> tuple[MealTemplate, ...]:
    required_tags = _required_dietary_tags(request.dietary_restrictions)
    budget_category = _budget_category(request)
    excluded_template_keys = (
        {"instant_noodles"} if budget_category != BUDGET_CATEGORY_LOW else set()
    )
    eligible_templates = tuple(
        template
        for template in templates
        if required_tags.issubset(template.dietary_tags)
        and template.key not in excluded_template_keys
        and not any(
            ingredient.product_key in DEFAULT_TEMPLATE_EXCLUSION_KEYS
            for ingredient in template.ingredients
        )
    )
    if not eligible_templates:
        raise ValueError("The meal catalogue has no templates for these restrictions.")

    required_meal_count = (request.days or 0) * 2
    products_by_key = {product.key: product for product in products}
    request_energy = request.cooking_energy or "normal"
    people = request.people or 1
    avoided_keys = frozenset(request.avoided_product_keys or ())
    preferred_keys = frozenset(request.preferred_product_keys or ())
    baseline_templates = (
        tuple(
            template
            for template in eligible_templates
            if template.catalogue_tier == "core"
        )
        + tuple(
            template
            for template in eligible_templates
            if template.catalogue_tier == "extended"
        )
        if required_meal_count >= sum(
            template.catalogue_tier == "core" for template in eligible_templates
        )
        else eligible_templates
    )
    budget_pressure = (
        request.budget is not None and budget_category == BUDGET_CATEGORY_LOW
    )

    def rank(candidates: tuple[MealTemplate, ...]) -> tuple[MealTemplate, ...]:
        # Rank templates with a small penalty for "leftover" (previously prepared)
        # templates when the pantry does not already contain matching prepared items.
        def _leftover_penalty(template: MealTemplate) -> int:
            # If a template is marked as leftover/quick and pantry coverage is zero,
            # apply a penalty so it's ranked later for early-day slots.
            pantry_cov = _template_pantry_coverage(template, request.pantry_items, products_by_key)
            if "leftover" in template.selection_tags and pantry_cov == 0:
                return 1
            return 0

        return tuple(
            template
            for _, template in sorted(
                enumerate(candidates),
                key=lambda indexed_template: (
                    (
                        _template_estimated_cost(
                            indexed_template[1],
                            people,
                            products_by_key,
                        )
                        if budget_pressure
                        else 0
                    ),
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
                    _leftover_penalty(indexed_template[1]),
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
    ranked = rank(eligible_templates)
    if budget_pressure:
        return _select_budget_sequence(request, ranked, products)
    return ranked


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
    budget_pressure: bool = False,
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
    if _budget_category(request) == BUDGET_CATEGORY_LOW:
        guidance.append(
            "Low budget category detected: meals target at least CAD$0.99 per person per meal."
        )
        budget_floor = _budget_floor(request)
        if request.budget is not None and budget_floor is not None and request.budget < budget_floor:
            guidance.append(
                f"Budget is below the minimum floor of CAD${budget_floor:.2f}; "
                "the final plan will show the shortfall."
            )
    if budget_pressure:
        guidance.append(
            "Budget pressure applied: lower-cost valid meal templates were preferred."
        )
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


def _coerce_pantry_candidates(
    pantry_items: list[str] | list[PantryCandidate] | None,
    products: tuple[Product, ...],
) -> tuple[PantryCandidate, ...]:
    if not pantry_items:
        return ()
    first_item = pantry_items[0]
    if isinstance(first_item, PantryCandidate):
        return tuple(pantry_items)
    return parse_pantry_candidates(pantry_items, products, source="text")


def _candidate_quantity(
    candidate: PantryCandidate,
    product: Product,
) -> float | None:
    if candidate.food_key != product.key or candidate.quantity_state != "known":
        return None
    if candidate.quantity_value is None:
        return None

    unit = candidate.quantity_unit
    if product.planning_unit == "each":
        if unit in {None, "each"}:
            return candidate.quantity_value
        if unit == "dozen":
            return candidate.quantity_value * 12
        return None

    if product.planning_unit == "g":
        if unit == "g":
            return candidate.quantity_value
        if unit == "kg":
            return candidate.quantity_value * 1000
        if unit == "lb":
            return candidate.quantity_value * GRAMS_PER_POUND
        if unit == "package":
            return candidate.quantity_value * product.package_size
        return None

    if product.planning_unit == "ml":
        if unit == "ml":
            return candidate.quantity_value
        if unit == "l":
            return candidate.quantity_value * 1000
        return None

    if product.planning_unit == "can":
        if unit == "can":
            return candidate.quantity_value
        if unit == "package":
            return candidate.quantity_value * product.package_size
        return None

    if product.planning_unit == "package":
        if unit == "package":
            return candidate.quantity_value
        return None

    return None


def _candidate_note(candidate: PantryCandidate, product: Product | None) -> str:
    if candidate.resolution_state != "matched" or product is None:
        return f"{candidate.original_text}: could not be matched or measured."
    if candidate.quantity_state == "known":
        quantity = _format_pantry_candidate_quantity(candidate, product)
        return f"{product.name}: used {quantity} from home."
    if candidate.quantity_state == "unknown":
        return f"{product.name}: known at home, amount unknown."
    return f"{candidate.original_text}: could not be matched or measured."


def _format_pantry_candidate_quantity(
    candidate: PantryCandidate,
    product: Product,
) -> str:
    quantity = _candidate_quantity(candidate, product)
    if quantity is None:
        return candidate.original_text
    return format_planning_quantity(quantity, product.planning_unit, product.name)


def _available_quantity(
    product: Product,
    pantry_items: list[str] | list[PantryCandidate] | None,
    products: tuple[Product, ...],
) -> float:
    candidates = _coerce_pantry_candidates(pantry_items, products)
    quantities = [
        quantity
        for candidate in candidates
        for quantity in [_candidate_quantity(candidate, product)]
        if quantity is not None
    ]
    return sum(quantities) if quantities else 0


def _build_shopping_items(
    requirements: dict[str, float],
    pantry_items: list[str] | list[PantryCandidate] | None,
    products: tuple[Product, ...],
) -> tuple[ShoppingItem, ...]:
    shopping_items: list[ShoppingItem] = []
    for product in products:
        required_amount = requirements.get(product.key, 0)
        available_amount = _available_quantity(product, pantry_items, products)
        shortfall = max(0, required_amount - available_amount)
        if shortfall <= 0:
            continue

        packages_needed = math.ceil(shortfall / product.package_size)
        quantity_label = f"{packages_needed} x {product.package_description}"
        base_price = packages_needed * product.package_price
        price_min = round(base_price * ESTIMATE_VARIATION_LOW, 2)
        price_max = round(base_price * ESTIMATE_VARIATION_HIGH, 2)
        shopping_items.append(
            ShoppingItem(
                name=product.name,
                quantity_label=quantity_label,
                estimated_price=round(base_price, 2),
                estimated_price_min=price_min,
                estimated_price_max=price_max,
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
    pantry_items: list[str] | list[PantryCandidate] | None,
    products: tuple[Product, ...],
) -> tuple[str, ...]:
    usage_notes: list[str] = []
    candidates = _coerce_pantry_candidates(pantry_items, products)
    products_by_key = {product.key: product for product in products}
    matched_products = {
        candidate.food_key
        for candidate in candidates
        if candidate.food_key is not None
    }
    for product in products:
        required_amount = requirements.get(product.key, 0)
        available_amount = _available_quantity(product, candidates, products)
        if required_amount <= 0 or available_amount <= 0:
            continue

        used_amount = min(required_amount, available_amount)
        quantity = format_planning_quantity(
            used_amount,
            product.planning_unit,
            product.name,
        )
        usage_notes.append(f"{product.name}: used {quantity} from home.")

    for candidate in candidates:
        product = products_by_key.get(candidate.food_key or "")
        if candidate.quantity_state == "known" and product is not None:
            continue
        if candidate.resolution_state == "matched" and candidate.quantity_state == "unknown":
            usage_notes.append(_candidate_note(candidate, product))
        elif candidate.resolution_state != "matched" or candidate.quantity_state == "invalid":
            usage_notes.append(_candidate_note(candidate, product))
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
        if (
            request.budget is not None
            and _sequence_purchase_cost(selected_templates, request, catalog.products)
            > request.budget
        ):
            selected_templates = _select_templates(request, templates, catalog.products)
            llm_selected = False
    meals_with_templates = _build_meals(request.days, selected_templates)
    requirements = _calculate_requirements(
        meals_with_templates,
        request.people,
    )
    _validate_catalog_coverage(requirements, selected_templates, catalog.products)
    budget_pressure = (
        request.budget is not None
        and _budget_category(request) == BUDGET_CATEGORY_LOW
    )
    pantry_context = (
        request.pantry_candidates
        if getattr(request, "pantry_candidates", None) is not None
        else request.pantry_items
    )

    return Plan(
        meals=tuple(meal for meal, _ in meals_with_templates),
        meal_templates=tuple(template for _, template in meals_with_templates),
        meal_selection_guidance=_describe_meal_selection(
            request,
            selected_templates,
            budget_pressure,
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
            pantry_context,
            catalog.products,
        ),
        pantry_usage=_describe_pantry_usage(
            requirements,
            pantry_context,
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
