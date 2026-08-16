from dataclasses import replace
import unittest

from catalog import load_simulated_catalog
from meal_catalogue import MealCatalogue, load_default_meal_catalogue
from planning import (
    generate_plan,
    select_meal_candidate_templates,
    validate_meal_candidate_keys,
)
from request_parser import ParsedRequest, parse_request


BASE_CASE = (
    "I have CAD$80 to feed 2 people for 4 days. "
    "We have low energy for cooking, already have enough rice and 7 eggs, "
    "and at least one person is lactose intolerant. "
    "We need lunch and dinner."
)


class TestPlanning(unittest.TestCase):
    def test_soft_food_preferences_rank_meals_without_becoming_hard_filters(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=1,
            cooking_energy="low",
            pantry_items=[],
            dietary_restrictions=[],
            avoided_product_keys=["eggs"],
            preferred_product_keys=["beans"],
        )

        plan = generate_plan(request)

        assert plan is not None
        self.assertEqual(plan.meals[0].dish, "Previously prepared bean stew with rice")
        self.assertIn(
            "Soft food preferences influenced meal ranking after dietary filters.",
            plan.meal_selection_guidance,
        )

    def test_rejects_unknown_or_conflicting_food_preference_keys(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=1,
            cooking_energy="low",
            pantry_items=[],
            dietary_restrictions=[],
            avoided_product_keys=["mushrooms"],
        )
        with self.assertRaisesRegex(ValueError, "Unknown food preference key"):
            generate_plan(request)

        request.avoided_product_keys = ["eggs"]
        request.preferred_product_keys = ["eggs"]
        with self.assertRaisesRegex(ValueError, "both avoided and preferred"):
            generate_plan(request)

    def test_validates_future_llm_candidates_against_local_hard_rules(self) -> None:
        request = ParsedRequest(dietary_restrictions=["lactose intolerance"])
        catalogue = load_default_meal_catalogue()
        candidate_keys = [
            catalogue.templates[1].key,
            catalogue.templates[0].key,
        ]

        candidates = validate_meal_candidate_keys(candidate_keys, request, catalogue)

        self.assertEqual([template.key for template in candidates], candidate_keys)
        with self.assertRaisesRegex(ValueError, "Unknown meal candidate key"):
            validate_meal_candidate_keys(["invented_meal"], request, catalogue)
        with self.assertRaisesRegex(ValueError, "must not contain duplicates"):
            validate_meal_candidate_keys(
                [candidate_keys[0], candidate_keys[0]],
                request,
                catalogue,
            )
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            validate_meal_candidate_keys([], request, catalogue)

        unsupported_request = ParsedRequest(
            dietary_restrictions=["gluten intolerance"]
        )
        with self.assertRaisesRegex(ValueError, "unsupported dietary restrictions"):
            validate_meal_candidate_keys(
                candidate_keys,
                unsupported_request,
                catalogue,
            )

        unsafe_template = replace(catalogue.templates[0], dietary_tags=())
        unsafe_catalogue = MealCatalogue(
            description=catalogue.description,
            templates=(unsafe_template,),
        )
        with self.assertRaisesRegex(ValueError, "dietary restrictions"):
            validate_meal_candidate_keys(
                [unsafe_template.key],
                request,
                unsafe_catalogue,
            )

    def test_generates_plan_from_validated_llm_candidate_order(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=1,
            cooking_energy="low",
            pantry_items=[],
            dietary_restrictions=[],
        )
        candidates = select_meal_candidate_templates(request)

        plan = generate_plan(
            request,
            meal_candidate_keys=(candidates[1].key, candidates[0].key),
        )

        assert plan is not None
        self.assertEqual(plan.meals[0].dish, candidates[1].dish)
        self.assertEqual(plan.meals[1].dish, candidates[0].dish)
        self.assertIn(
            "Optional LLM meal order was validated against known local templates.",
            plan.meal_selection_guidance,
        )

    def test_generates_eight_meals_within_the_budget(self) -> None:
        plan = generate_plan(parse_request(BASE_CASE))

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(len(plan.meals), 8)
        self.assertEqual(
            [meal.meal_slot for meal in plan.meals].count("Lunch"),
            4,
        )
        self.assertEqual(
            [meal.meal_slot for meal in plan.meals].count("Dinner"),
            4,
        )
        self.assertEqual(plan.estimated_total, 58.25)
        self.assertEqual(plan.budget_balance, 21.75)
        self.assertIn(
            "The plan uses the complete core library, so core catalogue order is preserved.",
            plan.meal_selection_guidance,
        )
        self.assertEqual(
            [meal.dish for meal in plan.meals],
            [
                "Roasted chicken, rice and vegetables",
                "Pan-fried rice with eggs and vegetables",
                "Previously prepared chicken, rice and vegetables",
                "Pasta with ground beef and tomato sauce",
                "Pasta with previously prepared meat sauce",
                "Quick bean and tomato stew with rice",
                "Previously prepared bean stew with rice",
                "Omelette with potatoes, onion and vegetables",
            ],
        )

    def test_prefers_low_effort_meals_for_a_short_low_energy_plan(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=1,
            cooking_energy="low",
            pantry_items=[],
            dietary_restrictions=[],
        )

        plan = generate_plan(request)

        assert plan is not None
        self.assertEqual(
            [meal.dish for meal in plan.meals],
            [
                "Pan-fried rice with eggs and vegetables",
                "Previously prepared chicken, rice and vegetables",
            ],
        )
        self.assertIn(
            "Cooking energy preference applied: low.",
            plan.meal_selection_guidance,
        )

    def test_uses_pantry_coverage_to_break_an_effort_tie(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=1,
            cooking_energy="low",
            pantry_items=["potatoes"],
            dietary_restrictions=[],
        )

        plan = generate_plan(request)

        assert plan is not None
        self.assertEqual(
            plan.meals[0].dish,
            "Omelette with potatoes, onion and vegetables",
        )

    def test_uses_exactly_the_seven_eggs(self) -> None:
        plan = generate_plan(parse_request(BASE_CASE))

        assert plan is not None
        egg_usage = " ".join(plan.pantry_usage)
        self.assertIn("7 eggs from the pantry", egg_usage)
        self.assertNotIn(
            "Large eggs",
            [item.name for item in plan.shopping_items],
        )

    def test_does_not_include_dairy_ingredients(self) -> None:
        plan = generate_plan(parse_request(BASE_CASE))

        assert plan is not None
        content = " ".join(
            [meal.dish for meal in plan.meals]
            + [item.name for item in plan.shopping_items]
        ).casefold()
        for dairy_product in ("milk", "cheese", "butter", "cream"):
            self.assertNotIn(dairy_product, content)

    def test_adapts_days_people_and_package_counts(self) -> None:
        request = ParsedRequest(
            budget=200,
            currency="CAD",
            people=3,
            days=6,
            cooking_energy="normal",
            pantry_items=["rice", "5 eggs"],
            dietary_restrictions=[],
        )
        plan = generate_plan(request)

        assert plan is not None
        self.assertEqual(len(plan.meals), 12)
        self.assertEqual(plan.people, 3)
        self.assertEqual(plan.days, 6)
        self.assertIn(
            "Large eggs",
            [item.name for item in plan.shopping_items],
        )
        self.assertGreater(plan.estimated_total, 58.25)
        self.assertIn(
            "Sheet-pan chicken with potatoes and vegetables",
            [meal.dish for meal in plan.meals],
        )
        self.assertIn(
            "Pasta with beans and tomato sauce",
            [meal.dish for meal in plan.meals],
        )

    def test_keeps_one_plan_when_the_budget_is_too_low(self) -> None:
        request = parse_request(BASE_CASE.replace("CAD$80", "CAD$20"))
        plan = generate_plan(request)

        assert plan is not None
        self.assertEqual(plan.estimated_total, 58.25)
        self.assertEqual(plan.budget_balance, -38.25)
        names = [item.name for item in plan.shopping_items]
        self.assertIn("Ground beef", names)

    def test_generates_a_plan_without_budget(self) -> None:
        request = parse_request(
            "Feed 2 people for 4 days. We have low energy for cooking, "
            "already have enough rice and 7 eggs, and at least one person is "
            "lactose intolerant. We need lunch and dinner."
        )

        plan = generate_plan(request)

        assert plan is not None
        self.assertIsNone(plan.budget)
        self.assertEqual(plan.estimated_total, 58.25)
        self.assertIsNone(plan.budget_balance)
        names = [item.name for item in plan.shopping_items]
        self.assertIn("Chicken thighs", names)

    def test_buys_rice_and_eggs_when_they_are_not_in_the_pantry(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=[],
            dietary_restrictions=[],
        )
        plan = generate_plan(request)

        assert plan is not None
        names = [item.name for item in plan.shopping_items]
        self.assertIn("Rice", names)
        self.assertIn("Large eggs", names)
        self.assertEqual(plan.estimated_total, 68.75)

    def test_rejects_an_unsupported_dietary_restriction(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=[],
            dietary_restrictions=["gluten intolerance"],
        )

        self.assertIsNone(generate_plan(request))

    def test_uses_one_kilogram_of_rice_without_buying_another_bag(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["1 kg of rice", "7 eggs"],
            dietary_restrictions=[],
        )
        plan = generate_plan(request)

        assert plan is not None
        self.assertNotIn(
            "Rice",
            [item.name for item in plan.shopping_items],
        )
        self.assertIn("1 kg", " ".join(plan.pantry_usage))

    def test_buys_rice_when_five_hundred_grams_is_not_enough(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["500 g of rice", "7 eggs"],
            dietary_restrictions=[],
        )
        plan = generate_plan(request)

        assert plan is not None
        self.assertIn(
            "Rice",
            [item.name for item in plan.shopping_items],
        )
        self.assertIn("500 g", " ".join(plan.pantry_usage))

    def test_understands_half_a_package_of_pasta(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=2,
            cooking_energy="low",
            pantry_items=["rice", "half a package of pasta", "4 eggs"],
            dietary_restrictions=[],
        )
        plan = generate_plan(request)

        assert plan is not None
        self.assertNotIn(
            "Dry pasta",
            [item.name for item in plan.shopping_items],
        )
        self.assertIn("250 g", " ".join(plan.pantry_usage))

    def test_adds_cans_and_half_a_dozen_eggs(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["rice", "2 cans of beans", "half a dozen eggs"],
            dietary_restrictions=[],
        )
        plan = generate_plan(request)

        assert plan is not None
        shopping_items = {
            item.name: item.quantity_label for item in plan.shopping_items
        }
        self.assertEqual(shopping_items["Canned beans"], "1 x 1 can")
        self.assertEqual(shopping_items["Large eggs"], "1 x 1 dozen")

    def test_separates_required_amount_from_fixed_package_quantity(self) -> None:
        plan = generate_plan(parse_request(BASE_CASE))

        assert plan is not None
        pasta = next(
            item for item in plan.shopping_items if item.name == "Dry pasta"
        )
        self.assertEqual(pasta.required_quantity, 500)
        self.assertEqual(pasta.purchase_quantity, 900)
        self.assertEqual(pasta.overage_quantity, 400)
        self.assertEqual(pasta.planning_unit, "g")
        self.assertEqual(pasta.package_count, 1)
        self.assertFalse(pasta.variable_weight)

    def test_marks_variable_weight_packages_as_estimates(self) -> None:
        original = load_simulated_catalog()
        products = tuple(
            replace(
                product,
                package_description="approximately 790 g package",
                package_size=790,
                instacart_quantity=790,
                instacart_unit="g",
                variable_weight=True,
            )
            if product.key == "chicken"
            else product
            for product in original.products
        )
        catalog = replace(original, products=products)

        plan = generate_plan(parse_request(BASE_CASE), catalog)

        assert plan is not None
        chicken = next(
            item for item in plan.shopping_items if item.name == "Chicken thighs"
        )
        self.assertEqual(chicken.required_quantity, 1200)
        self.assertEqual(chicken.package_count, 2)
        self.assertEqual(chicken.purchase_quantity, 1580)
        self.assertEqual(chicken.overage_quantity, 380)
        self.assertTrue(chicken.variable_weight)
        self.assertEqual(chicken.instacart_quantity, 1580)
        self.assertEqual(chicken.instacart_unit, "g")

    def test_converts_pounds_in_the_pantry_to_grams(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["1 lb of rice", "7 eggs"],
            dietary_restrictions=[],
        )

        plan = generate_plan(request)

        assert plan is not None
        rice = next(
            item for item in plan.shopping_items if item.name == "Rice"
        )
        self.assertAlmostEqual(rice.required_quantity, 546.40763, places=5)
        self.assertEqual(rice.purchase_quantity, 2000)
        self.assertIn("453.6 g", " ".join(plan.pantry_usage))

    def test_converts_litres_and_millilitres_to_one_volume_unit(self) -> None:
        request = ParsedRequest(
            budget=100,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["0.2 L of oil", "rice", "7 eggs"],
            dietary_restrictions=[],
        )

        plan = generate_plan(request)

        assert plan is not None
        self.assertNotIn(
            "Vegetable oil",
            [item.name for item in plan.shopping_items],
        )
        self.assertIn("160 ml", " ".join(plan.pantry_usage))


if __name__ == "__main__":
    unittest.main()
