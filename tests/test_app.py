import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import format_plan, main, review_request, save_plan
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
        shopping_location="Toronto",
        selected_store="No Frills",
    )


class TestTerminal(unittest.TestCase):
    def test_displays_identified_request_and_plan(self) -> None:
        request_text = (
            "I have $80 to feed 2 people for 4 days. "
            "We have low energy for cooking, we already have rice and 7 eggs, "
            "and at least one person has lactose intolerance. "
            "I am shopping in Toronto at No Frills."
        )

        with (
            patch("builtins.input", side_effect=[request_text, "y", "n"]),
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
        self.assertIn("Shopping location: Toronto", content)
        self.assertIn("Selected store: No Frills", content)
        self.assertIn("Information confirmed", content)
        self.assertIn("MEAL PLAN", content)
        self.assertIn("Estimated total: CAD$58.25", content)
        self.assertIn("Budget balance: CAD$21.75", content)

    def test_asks_only_for_missing_information(self) -> None:
        responses = [
            "I need help planning meals.",
            "80",
            "2",
            "4",
            "1",
            "rice, 7 eggs",
            "lactose intolerance",
            "Toronto",
            "No Frills",
            "y",
            "n",
        ]

        with (
            patch("builtins.input", side_effect=responses) as user_input,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        content = output.getvalue()
        self.assertEqual(user_input.call_count, 11)
        self.assertIn("Budget: CAD$80", content)
        self.assertIn("People: 2", content)
        self.assertIn("Days: 4", content)
        self.assertIn("Cooking energy: low", content)
        self.assertIn("Pantry items: rice, 7 eggs", content)
        self.assertIn("Dietary restrictions: lactose intolerance", content)
        self.assertIn("Shopping location: Toronto", content)
        self.assertIn("Selected store: No Frills", content)
        self.assertIn("MEAL PLAN", content)

    def test_requires_one_store_instead_of_accepting_any_store(self) -> None:
        responses = [
            "I have CAD$80 for 2 people for 4 days with normal cooking energy. "
            "I already have rice and 7 eggs. I have no dietary restrictions. "
            "I am in Toronto and I have no store preference.",
            "",
            "No Frills",
            "y",
            "n",
        ]

        with (
            patch("builtins.input", side_effect=responses) as user_input,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            main()

        content = output.getvalue()
        self.assertTrue(
            any(
                "current pilot store is No Frills" in call.args[0]
                for call in user_input.call_args_list
            )
        )
        self.assertIn("This version supports only No Frills", content)
        self.assertIn("Selected store: No Frills", content)

    def test_saves_plan_and_both_instacart_files(self) -> None:
        request_text = (
            "I have CAD$80 for 2 people for 4 days with low cooking energy. "
            "I already have rice and 7 eggs. I have no dietary restrictions. "
            "I am shopping in Toronto at No Frills."
        )
        with (
            patch("builtins.input", side_effect=[request_text, "y", "y"]),
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
        self.assertIn("Shopping List → Paste items", content)
        self.assertIn("labels for your dietary needs", content)

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

    def test_corrects_location_and_store_without_restarting(self) -> None:
        request_data = _base_request()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "n",
                    "7",
                    "Vancouver",
                    "Toronto",
                    "n",
                    "8",
                    "Loblaws",
                    "No Frills",
                    "y",
                ],
            ),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            result = review_request(request_data)

        self.assertEqual(result.shopping_location, "Toronto")
        self.assertEqual(result.selected_store, "No Frills")
        self.assertIn("supports only Toronto, ON", output.getvalue())
        self.assertIn("supports only No Frills", output.getvalue())

    def test_formats_every_plan_section_in_english(self) -> None:
        plan = generate_plan(_base_request())

        assert plan is not None
        content = format_plan(plan)
        self.assertIn("MEAL PLAN", content)
        self.assertIn("MEAL PREP GUIDANCE", content)
        self.assertIn("SHOPPING LIST", content)
        self.assertIn("Estimated total: CAD$58.25", content)
        self.assertIn("Price source:", content)
        self.assertIn("Shopping location: Toronto", content)
        self.assertIn("Selected store: No Frills", content)
        self.assertIn("one simulated price catalogue", content)
        self.assertIn("PANTRY ITEMS USED", content)
        self.assertNotIn("ALTERNATIVA", content)
        self.assertNotIn("savings", content.casefold())

    def test_reports_shortfall_without_switching_to_an_economic_plan(self) -> None:
        plan = generate_plan(_base_request(budget=20))

        assert plan is not None
        content = format_plan(plan)
        self.assertEqual(plan.estimated_total, 58.25)
        self.assertEqual(plan.budget_balance, -38.25)
        self.assertIn("Budget shortfall: CAD$38.25", content)
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
            self.assertIn("Shopping location: Toronto", content)
            self.assertIn("Selected store: No Frills", content)


if __name__ == "__main__":
    unittest.main()
