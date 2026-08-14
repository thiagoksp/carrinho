import unittest

from web_app import HOST, build_request, create_plan, render_page


def _reference_form() -> dict[str, str]:
    return {
        "budget": "80",
        "people": "2",
        "days": "4",
        "cooking_energy": "low",
        "pantry_items": "rice, 7 eggs",
        "dietary_restrictions": "lactose intolerance",
        "foods_to_avoid": "",
        "foods_to_prefer": "",
    }


class TestWebApp(unittest.TestCase):
    def test_binds_to_the_local_computer_only(self) -> None:
        self.assertEqual(HOST, "127.0.0.1")

    def test_builds_the_reference_request_and_plan(self) -> None:
        request = build_request(_reference_form())
        plan = create_plan(_reference_form())

        self.assertEqual(request.currency, "CAD")
        self.assertEqual(request.pantry_items, ["rice", "7 eggs"])
        self.assertEqual(request.dietary_restrictions, ["lactose intolerance"])
        self.assertEqual(plan.estimated_total, 58.25)
        self.assertEqual(plan.budget_balance, 21.75)

    def test_resolves_food_preferences_and_new_lines(self) -> None:
        values = _reference_form()
        values["pantry_items"] = "rice\n7 eggs"
        values["foods_to_avoid"] = "beans and onions"
        values["foods_to_prefer"] = "chicken, eggs"

        request = build_request(values)

        self.assertEqual(request.pantry_items, ["rice", "7 eggs"])
        self.assertEqual(request.avoided_product_keys, ["beans", "onions"])
        self.assertEqual(request.preferred_product_keys, ["chicken", "eggs"])

    def test_rejects_invalid_or_conflicting_values(self) -> None:
        cases = (
            ("budget", "0", "budget greater than zero"),
            ("budget", "80 dollars", "valid budget in CAD"),
            ("people", "2.5", "valid number of people"),
            ("people", "13", "between 1 and 12"),
            ("days", "15", "between 1 and 14"),
            ("dietary_restrictions", "gluten-free", "supported dietary restriction"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                values = _reference_form()
                values[field] = value
                with self.assertRaisesRegex(ValueError, message):
                    build_request(values)

        values = _reference_form()
        values["foods_to_avoid"] = "eggs"
        values["foods_to_prefer"] = "eggs"
        with self.assertRaisesRegex(ValueError, "both avoided and preferred"):
            build_request(values)

    def test_renders_escaped_values_errors_and_plan(self) -> None:
        values = _reference_form()
        values["pantry_items"] = "<script>alert(1)</script>"

        page = render_page(
            values,
            plan=create_plan(_reference_form()),
            error="Bad <value>",
        )

        self.assertIn("Bad &lt;value&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("Your Carrinho plan", page)
        self.assertIn("Estimated total: CAD$58.25", page)
        self.assertIn("No request is sent to Instacart", page)


if __name__ == "__main__":
    unittest.main()
