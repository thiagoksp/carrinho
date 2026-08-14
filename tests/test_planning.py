import unittest

from planning import generate_plan
from request_parser import ParsedRequest, parse_request


BASE_CASE = (
    "I have CAD$80 to feed 2 people for 4 days. "
    "We have low energy for cooking, already have enough rice and 7 eggs, "
    "and at least one person is lactose intolerant. "
    "We need lunch and dinner. I am in Toronto and will shop at No Frills."
)


class TestPlanning(unittest.TestCase):
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

    def test_keeps_one_plan_when_the_budget_is_too_low(self) -> None:
        request = parse_request(BASE_CASE.replace("CAD$80", "CAD$20"))
        plan = generate_plan(request)

        assert plan is not None
        self.assertEqual(plan.estimated_total, 58.25)
        self.assertEqual(plan.budget_balance, -38.25)
        names = [item.name for item in plan.shopping_items]
        self.assertIn("Ground beef", names)
        self.assertIn("Chicken thighs", names)

    def test_rejects_a_store_or_location_outside_the_pilot(self) -> None:
        for location, store in (
            ("Vancouver, BC", "No Frills"),
            ("Toronto", "Walmart"),
        ):
            with self.subTest(location=location, store=store):
                request = parse_request(BASE_CASE)
                request.shopping_location = location
                request.selected_store = store

                self.assertIsNone(generate_plan(request))

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
        self.assertIn("0.5 kg", " ".join(plan.pantry_usage))

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
        self.assertIn("0.25 kg", " ".join(plan.pantry_usage))

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
        self.assertEqual(shopping_items["Canned beans"], "1 can")
        self.assertEqual(shopping_items["Large eggs"], "1 dozen")


if __name__ == "__main__":
    unittest.main()
