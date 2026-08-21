import unittest

from food_rules import (
    build_food_rules_for_avoided_products,
    build_food_rules_for_dietary_restrictions,
    normalize_food_rule_value,
)
from meal_catalogue import MealCatalogue, MealIngredient, MealTemplate
from planning import _required_dietary_tags, validate_meal_candidate_keys
from request_parser import ParsedRequest


class TestFoodRules(unittest.TestCase):
    def test_normalizes_supported_aliases(self) -> None:
        self.assertEqual(normalize_food_rule_value("vegan_diet"), "vegan")
        self.assertEqual(normalize_food_rule_value("gluten-free"), "avoid gluten ingredients")
        self.assertEqual(normalize_food_rule_value("avoid_gluten_ingredients"), "avoid gluten ingredients")

    def test_builds_rules_for_dietary_restrictions(self) -> None:
        rules = build_food_rules_for_dietary_restrictions([
            "vegan",
            "avoid gluten ingredients",
        ])
        self.assertEqual(
            [rule.code for rule in rules],
            ["diet.vegan", "diet.avoid_gluten_ingredients"],
        )

    def test_avoided_products_are_deduplicated(self) -> None:
        rules = build_food_rules_for_avoided_products(["beans", "beans", "mushrooms"])
        self.assertEqual(
            [rule.target_key for rule in rules],
            ["beans", "mushrooms"],
        )

    def test_required_tags_cover_vegan_and_gluten(self) -> None:
        self.assertEqual(
            _required_dietary_tags(["vegan"]),
            frozenset({"vegan", "vegetarian"}),
        )
        self.assertEqual(
            _required_dietary_tags(["avoid gluten ingredients"]),
            frozenset({"no-gluten-ingredients"}),
        )

    def test_validate_meal_candidate_keys_applies_required_rules(self) -> None:
        vegan_template = MealTemplate(
            key="vegan_rice",
            dish="Vegan rice bowl",
            catalogue_tier="core",
            cooking_energy="normal",
            dietary_tags=("vegan", "vegetarian"),
            selection_tags=("quick",),
            ingredients=(MealIngredient("rice", 1.0, "g"),),
        )
        vegetarian_template = MealTemplate(
            key="vegetarian_pasta",
            dish="Vegetarian pasta",
            catalogue_tier="core",
            cooking_energy="normal",
            dietary_tags=("vegetarian",),
            selection_tags=("quick",),
            ingredients=(MealIngredient("pasta", 1.0, "g"),),
        )
        catalogue = MealCatalogue(
            description="test",
            templates=(vegan_template, vegetarian_template),
        )

        request = ParsedRequest(dietary_restrictions=["vegan"])
        self.assertEqual(
            validate_meal_candidate_keys(("vegan_rice",), request, catalogue),
            (vegan_template,),
        )
        with self.assertRaisesRegex(ValueError, "dietary restrictions"):
            validate_meal_candidate_keys(("vegetarian_pasta",), request, catalogue)


if __name__ == "__main__":
    unittest.main()
