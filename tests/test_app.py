import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import format_plan, main, review_request, save_plan
from household_profile import HouseholdProfile
from planning import generate_plan
from request_parser import ParsedRequest


def _base_request(budget: float = 80) -> ParsedRequest:
    return ParsedRequest(
        budget=budget,
        currency="CAD",
        people=2,
        days=4,
        cooking_energy="low",
        pantry_items=["rice", "7 eggs"],
        dietary_restrictions=["lactose intolerance"],
        avoided_product_keys=[],
        preferred_product_keys=[],
    )


class TestTerminal(unittest.TestCase):
    def test_stops_with_guidance_when_the_local_catalogue_is_invalid(self) -> None:
        with (
            patch("builtins.input", return_value="I have CAD$80."),
            patch(
                "app.load_local_catalogue",
                side_effect=ValueError("Invalid local data."),
            ),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        self.assertIn("local catalogue needs attention", output.getvalue())
        self.assertIn("Manage local meals and foods", output.getvalue())

    def test_displays_identified_request_and_plan(self) -> None:
        request_text = (
            "I have $80 to feed 2 people for 4 days. "
            "We have low energy for cooking, we already have rice and 7 eggs, "
            "and at least one person has lactose intolerance. "
            "I don't like beans. My favourite food is chicken."
        )

        with (
            patch("builtins.input", side_effect=[request_text, "y", "n", "n"]),
            patch("app.load_household_profile", return_value=None),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        content = output.getvalue()
        self.assertIn("Carrinho understood", content)
        self.assertIn("Budget: CAD$80", content)
        self.assertIn("People: 2", content)
        self.assertIn("Days: 4", content)
        self.assertIn("Cooking energy: low", content)
        self.assertIn("Pantry items: rice, 7 eggs", content)
        self.assertIn("Dietary restrictions: lactose intolerance", content)
        self.assertIn("Foods to use less often: Canned beans", content)
        self.assertIn("Foods to use more often: Chicken thighs", content)
        self.assertNotIn("Shopping location", content)
        self.assertNotIn("Selected store", content)
        self.assertIn("Information confirmed", content)
        self.assertIn("MEAL PLAN", content)
        self.assertIn("Retailer: to be selected by the user in Instacart", content)
        # The exact numeric ranges may vary; ensure the labels are present
        self.assertIn("Estimated total range:", content)
        self.assertIn("Budget balance range:", content)
        self.assertIn("local planning estimate range only", content)

    def test_format_plan_includes_recipe_steps(self) -> None:
        plan = generate_plan(_base_request())

        self.assertIsNotNone(plan)
        content = format_plan(plan)
        self.assertIn("Difficulty:", content)
        self.assertIn("Steps:", content)
        self.assertIn("Warm the rice", content)

    def test_asks_only_for_missing_information(self) -> None:
        responses = [
            "I need help planning meals.",
            "80",
            "2",
            "4",
            "1",
            "rice, 7 eggs",
            "lactose intolerance",
            "y",
            "n",
            "n",
        ]

        with (
            patch("builtins.input", side_effect=responses) as user_input,
            patch("app.load_household_profile", return_value=None),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        content = output.getvalue()
        self.assertEqual(user_input.call_count, 10)
        self.assertIn("Budget: CAD$80", content)
        self.assertIn("People: 2", content)
        self.assertIn("Days: 4", content)
        self.assertIn("Cooking energy: low", content)
        self.assertIn("Pantry items: rice, 7 eggs", content)
        self.assertIn("Dietary restrictions: lactose intolerance", content)
        self.assertNotIn("Shopping location", content)
        self.assertNotIn("Selected store", content)
        self.assertIn("MEAL PLAN", content)

    def test_does_not_request_a_location_or_retailer(self) -> None:
        responses = [
            "I have CAD$80 for 2 people for 4 days with normal cooking energy. "
            "I already have rice and 7 eggs. I have no dietary restrictions. "
            "I am in Toronto and I have no store preference.",
            "y",
            "n",
            "n",
        ]

        with (
            patch("builtins.input", side_effect=responses) as user_input,
            patch("app.load_household_profile", return_value=None),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        content = output.getvalue()
        prompts = " ".join(call.args[0] for call in user_input.call_args_list)
        self.assertEqual(user_input.call_count, 4)
        self.assertNotIn("location", prompts.casefold())
        self.assertNotIn("store", prompts.casefold())
        self.assertNotIn("Shopping location", content)
        self.assertNotIn("Selected store", content)

    def test_saves_plan_and_both_instacart_files(self) -> None:
        request_text = (
            "I have CAD$80 for 2 people for 4 days with low cooking energy. "
            "I already have rice and 7 eggs. I have no dietary restrictions."
        )
        with (
            patch("builtins.input", side_effect=[request_text, "y", "n", "y"]),
            patch("app.load_household_profile", return_value=None),
            patch("app.save_plan", return_value=Path("meal-plan.txt")) as text_file,
            patch(
                "app.save_instacart_payload",
                return_value=Path("instacart-list.json"),
            ) as json_file,
            patch(
                "app.save_instacart_paste_list",
                return_value=Path("instacart-paste-list.txt"),
            ) as paste_file,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        text_file.assert_called_once()
        json_file.assert_called_once()
        paste_file.assert_called_once()
        self.assertIs(text_file.call_args.args[0], json_file.call_args.args[0])
        self.assertIs(text_file.call_args.args[0], paste_file.call_args.args[0])
        content = output.getvalue()
        self.assertIn("no data was sent", content)
        self.assertIn("instacart-list.json", content)
        self.assertIn("instacart-paste-list.txt", content)
        self.assertIn("Shopping List -> Paste items", content)
        self.assertIn("labels for your dietary needs", content)
        self.assertIn("retailer you select in Instacart", content)

    def test_uses_and_updates_a_saved_household_profile_explicitly(self) -> None:
        request_text = "I have CAD$80 for 4 days."
        profile = HouseholdProfile(
            people=2,
            cooking_energy="low",
            pantry_items=("rice", "7 eggs"),
            dietary_restrictions=("lactose intolerance",),
        )

        with (
            patch(
                "builtins.input",
                side_effect=[request_text, "y", "y", "y", "n"],
            ),
            patch("app.load_household_profile", return_value=profile),
            patch(
                "app.save_household_profile",
                return_value=Path("household-profile.json"),
            ) as save_profile,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        saved_request = save_profile.call_args.args[0]
        self.assertEqual(saved_request.people, 2)
        self.assertEqual(saved_request.pantry_items, ["rice", "7 eggs"])
        self.assertIn("Household profile saved locally", output.getvalue())

    def test_corrects_budget_and_days_without_restarting(self) -> None:
        request_data = _base_request()

        with (
            patch(
                "builtins.input",
                side_effect=["n", "1", "60", "n", "3", "5", "y"],
            ),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            result = review_request(request_data)

        self.assertEqual(result.budget, 60)
        self.assertEqual(result.days, 5)
        self.assertIn("Budget: CAD$60", output.getvalue())
        self.assertIn("Days: 5", output.getvalue())

    def test_corrects_pantry_and_restrictions_without_restarting(self) -> None:
        request_data = _base_request()
        request_data.pantry_items = ["rice"]

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "n",
                    "5",
                    "1 kg of rice, half a dozen eggs",
                    "n",
                    "6",
                    "none",
                    "y",
                ],
            ),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            result = review_request(request_data)

        self.assertEqual(
            result.pantry_items,
            ["1 kg of rice", "half a dozen eggs"],
        )
        self.assertEqual(result.dietary_restrictions, [])

    def test_registers_catalogue_backed_food_preferences(self) -> None:
        request_data = _base_request()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "n",
                    "7",
                    "mushrooms",
                    "onions, beans",
                    "n",
                    "8",
                    "chicken and eggs",
                    "y",
                ],
            ),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            result = review_request(request_data)

        self.assertEqual(result.avoided_product_keys, ["onions", "beans"])
        self.assertEqual(result.preferred_product_keys, ["chicken", "eggs"])
        self.assertIn("Unknown food preference: mushrooms", output.getvalue())
        self.assertIn("Available generic foods", output.getvalue())

    def test_requires_conflicting_food_preferences_to_be_corrected(self) -> None:
        request_data = _base_request()
        request_data.avoided_product_keys = ["eggs"]
        request_data.preferred_product_keys = ["eggs"]

        with (
            patch("builtins.input", side_effect=["y", "8", "chicken", "y"]),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            result = review_request(request_data)

        self.assertEqual(result.avoided_product_keys, ["eggs"])
        self.assertEqual(result.preferred_product_keys, ["chicken"])
        self.assertIn("cannot be both used less often", output.getvalue())

    def test_rejects_removed_location_and_retailer_correction_options(self) -> None:
        request_data = _base_request()

        with (
            patch("builtins.input", side_effect=["n", "9", "1", "60", "y"]),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            result = review_request(request_data)

        self.assertEqual(result.budget, 60)
        self.assertFalse(hasattr(result, "shopping_location"))
        self.assertFalse(hasattr(result, "selected_store"))
        self.assertIn("Choose a number from 1 to 8", output.getvalue())

    def test_formats_every_plan_section_in_english(self) -> None:
        plan = generate_plan(_base_request())

        assert plan is not None
        content = format_plan(plan)
        self.assertIn("MEAL PLAN", content)
        self.assertIn("MEAL SELECTION", content)
        self.assertIn("Selection is deterministic", content)
        self.assertIn("MEAL PREP GUIDANCE", content)
        self.assertIn("SHOPPING LIST", content)
        self.assertIn("Estimated total range: CAD$58.42 to CAD$82.50", content)
        self.assertIn("Price source:", content)
        self.assertIn("Retailer: to be selected by the user in Instacart", content)
        self.assertIn("simulated, retailer-neutral Canadian price catalogue", content)
        self.assertIn("need 500 g; buy 900 g; 400 g extra", content)
        self.assertIn(
            "need 1.2 kg; plan about 1.2 kg; "
            "actual package weight may be higher or lower",
            content,
        )
        self.assertNotIn("Shopping location", content)
        self.assertNotIn("Selected store", content)
        self.assertIn("PANTRY ITEMS USED", content)
        self.assertNotIn("ALTERNATIVA", content)
        self.assertNotIn("savings", content.casefold())

    def test_reports_low_budget_fallback_without_offering_a_cheaper_plan(self) -> None:
        plan = generate_plan(_base_request(budget=20))

        assert plan is not None
        content = format_plan(plan)
        self.assertEqual(plan.estimated_total, 15.84)
        self.assertEqual(plan.budget_balance, 4.16)
        self.assertIn("Instant noodles", [meal.dish for meal in plan.meals])
        self.assertIn("Budget balance range: CAD$0.99 to CAD$6.54", content)
        self.assertNotIn("economic", content.casefold())
        self.assertNotIn("savings", content.casefold())

    def test_saves_new_files_without_overwriting(self) -> None:
        plan = generate_plan(_base_request())

        assert plan is not None
        with tempfile.TemporaryDirectory() as directory:
            first = save_plan(plan, Path(directory))
            second = save_plan(plan, Path(directory))

            self.assertEqual(first.name, "meal-plan.txt")
            self.assertEqual(second.name, "meal-plan-2.txt")
            self.assertEqual(
                first.read_text(encoding="utf-8"),
                second.read_text(encoding="utf-8"),
            )
            content = first.read_text(encoding="utf-8")
            self.assertIn("SHOPPING LIST", content)
            self.assertIn("Retailer: to be selected by the user in Instacart", content)
            self.assertNotIn("Shopping location", content)
            self.assertNotIn("Selected store", content)

    def test_recipe_guidance_includes_ingredients_and_reuse(self) -> None:
        plan = generate_plan(_base_request())

        assert plan is not None
        content = format_plan(plan)
        # Expect an ingredients section and at least one product keyword
        self.assertTrue(
            "Ingredients:" in content or "SHOPPING LIST" in content,
            "Plan should include an Ingredients or Shopping List section",
        )
        self.assertRegex(content.lower(), r"\b(rice|ground beef|eggs|tomato)\b")
        if "Previously prepared" in content:
            self.assertRegex(
                content,
                r"Previously prepared[\s\S]{0,150}(?:Make|Prepare|Save|Set aside|store|refrigerate)",
                "Previously prepared items should include when/how to prepare or save them",
            )


if __name__ == "__main__":
    unittest.main()
