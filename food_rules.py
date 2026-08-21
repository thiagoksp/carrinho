"""Versioned household food rules for Carrinho."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata


_SUPPORTED_DIETARY_PATTERN_TARGETS = {
    "lactose_intolerance": "lactose-free",
    "vegetarian": "vegetarian",
    "vegan": "vegan",
    "avoid_gluten_ingredients": "no-gluten-ingredients",
}


def _remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


@dataclass(frozen=True)
class FoodRule:
    """One household food-rule decision after local validation."""

    code: str
    scope_type: str = "household"
    target_type: str = "dietary_pattern"
    target_key: str = ""
    action: str = "exclude"
    reason_type: str = "dietary_pattern"
    enforcement: str = "required"
    source: str = "preset"
    active: bool = True


SUPPORTED_DIETARY_RESTRICTIONS = (
    "lactose intolerance",
    "vegetarian",
    "vegan",
    "avoid gluten ingredients",
)

PRESET_RULES: dict[str, FoodRule] = {
    "lactose intolerance": FoodRule(
        code="diet.lactose_intolerance",
        target_type="dietary_pattern",
        target_key="lactose_intolerance",
        action="exclude",
        reason_type="intolerance",
        enforcement="required",
        source="preset",
        active=True,
    ),
    "vegetarian": FoodRule(
        code="diet.vegetarian",
        target_type="dietary_pattern",
        target_key="vegetarian",
        action="exclude",
        reason_type="dietary_pattern",
        enforcement="required",
        source="preset",
        active=True,
    ),
    "vegan": FoodRule(
        code="diet.vegan",
        target_type="dietary_pattern",
        target_key="vegan",
        action="exclude",
        reason_type="dietary_pattern",
        enforcement="required",
        source="preset",
        active=True,
    ),
    "avoid gluten ingredients": FoodRule(
        code="diet.avoid_gluten_ingredients",
        target_type="dietary_pattern",
        target_key="avoid_gluten_ingredients",
        action="exclude",
        reason_type="dietary_pattern",
        enforcement="required",
        source="preset",
        active=True,
    ),
}

LEGACY_DIETARY_ALIASES = {
    "dairy free": "lactose intolerance",
    "dairy-free": "lactose intolerance",
    "dairy_free": "lactose intolerance",
    "lactose free": "lactose intolerance",
    "lactose-free": "lactose intolerance",
    "lactose_free": "lactose intolerance",
    "lactose intolerant": "lactose intolerance",
    "lactose_intolerance": "lactose intolerance",
    "no dairy": "lactose intolerance",
    "vegetarian diet": "vegetarian",
    "vegetarian_diet": "vegetarian",
    "vegetarian-diet": "vegetarian",
    "vegan diet": "vegan",
    "vegan_diet": "vegan",
    "vegan-diet": "vegan",
    "gluten free": "avoid gluten ingredients",
    "gluten-free": "avoid gluten ingredients",
    "gluten_free": "avoid gluten ingredients",
    "no gluten": "avoid gluten ingredients",
    "no_gluten": "avoid gluten ingredients",
    "no gluten ingredients": "avoid gluten ingredients",
    "no_gluten_ingredients": "avoid gluten ingredients",
    "no-gluten-ingredients": "avoid gluten ingredients",
    "avoid gluten": "avoid gluten ingredients",
    "avoid_gluten": "avoid gluten ingredients",
    "avoid_gluten_ingredients": "avoid gluten ingredients",
    "avoid-gluten-ingredients": "avoid gluten ingredients",
}

RESTRICTION_TO_TAG = {
    "lactose intolerance": "lactose-free",
    "vegetarian": "vegetarian",
    "vegan": "vegan",
    "avoid gluten ingredients": "no-gluten-ingredients",
}


def normalize_food_rule_value(value: str) -> str:
    """Return the canonical household restriction name for a user value."""
    if not isinstance(value, str):
        raise ValueError("Dietary restrictions must be text values.")
    normalized = _remove_accents(value.strip())
    normalized = normalized.replace("_", " ").replace("-", " ")
    if not normalized:
        raise ValueError("Dietary restrictions must not be empty.")
    canonical = LEGACY_DIETARY_ALIASES.get(normalized, normalized)
    if canonical in SUPPORTED_DIETARY_RESTRICTIONS:
        return canonical
    for supported in SUPPORTED_DIETARY_RESTRICTIONS:
        support_key = _remove_accents(supported).replace("_", " ").replace("-", " ")
        if canonical == support_key:
            return supported
    raise ValueError(f"Unsupported dietary restriction: {value}.")


def normalize_food_rule_values(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    """Normalize and deduplicate a household restriction list."""
    if values is None:
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        canonical = normalize_food_rule_value(value)
        if canonical not in seen:
            normalized.append(canonical)
            seen.add(canonical)
    return tuple(normalized)


def build_food_rules_for_dietary_restrictions(
    restrictions: list[str] | tuple[str, ...] | None,
) -> tuple[FoodRule, ...]:
    """Create the required deterministic FoodRule instances for dietary needs."""
    normalized = normalize_food_rule_values(restrictions)
    return tuple(PRESET_RULES[restriction] for restriction in normalized)


def restriction_to_tag(restriction: str) -> str:
    """Map a supported restriction to its required meal tag."""
    canonical = normalize_food_rule_value(restriction)
    return RESTRICTION_TO_TAG[canonical]


def build_food_rules_for_avoided_products(
    avoided_product_keys: list[str] | tuple[str, ...] | None,
) -> tuple[FoodRule, ...]:
    """Create absolute exclusion rules for foods the household wants left out."""
    if not avoided_product_keys:
        return ()
    rules: list[FoodRule] = []
    seen: set[str] = set()
    for product_key in avoided_product_keys:
        normalized_key = str(product_key).strip()
        if not normalized_key or normalized_key in seen:
            continue
        seen.add(normalized_key)
        rules.append(
            FoodRule(
                code=f"food.{normalized_key}.exclude",
                scope_type="household",
                target_type="catalogue_food",
                target_key=normalized_key,
                action="exclude",
                reason_type="preference",
                enforcement="required",
                source="user",
                active=True,
            )
        )
    return tuple(rules)


def build_food_rule_summary(
    dietary_restrictions: list[str] | tuple[str, ...] | None,
    avoided_product_keys: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Return a human-readable summary of active household rules."""
    summary: list[str] = []
    for restriction in normalize_food_rule_values(dietary_restrictions):
        summary.append(restriction)
    for product_key in avoided_product_keys or ():
        summary.append(f"no {product_key}")
    return tuple(summary)


__all__ = [
    "FoodRule",
    "LEGACY_DIETARY_ALIASES",
    "PRESET_RULES",
    "RESTRICTION_TO_TAG",
    "SUPPORTED_DIETARY_RESTRICTIONS",
    "build_food_rule_summary",
    "build_food_rules_for_avoided_products",
    "build_food_rules_for_dietary_restrictions",
    "normalize_food_rule_value",
    "normalize_food_rule_values",
    "restriction_to_tag",
]
