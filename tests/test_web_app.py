import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from web_app import (
    CSRF_TOKEN,
    CarrinhoHandler,
    HOST,
    build_request,
    create_plan,
    render_customization_page,
    render_page,
)


def _reference_form() -> dict[str, str]:
    return {
        "budget": "80",
        "people": "2",
        "days": "4",
        "cooking_energy": "low",
        "pantry_items": "rice, 7 eggs",
        "dietary_lactose_intolerance": "on",
        "dietary_vegetarian": "",
        "dietary_vegan": "",
        "dietary_avoid_gluten_ingredients": "",
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
        self.assertEqual(plan.estimated_total, 62.75)
        self.assertEqual(plan.budget_balance, 17.25)

    def test_builds_a_plan_without_budget(self) -> None:
        values = _reference_form()
        values["budget"] = ""

        request = build_request(values)
        plan = create_plan(values)

        self.assertIsNone(request.budget)
        self.assertEqual(request.currency, "CAD")
        self.assertEqual(plan.estimated_total, 62.75)
        self.assertIsNone(plan.budget_balance)
        self.assertIn("No budget provided.", render_page(values, plan=plan))

    def test_builds_a_minimal_quick_start_plan(self) -> None:
        values = {
            "budget": "",
            "people": "2",
            "days": "4",
            "cooking_energy": "normal",
            "pantry_items": "",
            "dietary_restrictions": "none",
            "foods_to_avoid": "",
            "foods_to_prefer": "",
        }

        request = build_request(values)
        plan = create_plan(values)

        self.assertIsNone(request.budget)
        self.assertEqual(request.people, 2)
        self.assertEqual(request.days, 4)
        self.assertEqual(request.cooking_energy, "normal")
        self.assertEqual(request.pantry_items, [])
        self.assertEqual(request.dietary_restrictions, [])
        self.assertGreater(plan.estimated_total, 0)
        self.assertIn("No budget provided.", render_page(values, plan=plan))

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
            ("dietary_restrictions", "paleo", "supported dietary restriction"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                values = _reference_form()
                if field == "dietary_restrictions":
                    values["dietary_lactose_intolerance"] = ""
                    values["dietary_vegetarian"] = ""
                    values["dietary_vegan"] = ""
                    values["dietary_avoid_gluten_ingredients"] = ""
                values[field] = value
                with self.assertRaisesRegex(ValueError, message):
                    build_request(values)

        values = _reference_form()
        values["foods_to_avoid"] = "eggs"
        values["foods_to_prefer"] = "eggs"
        with self.assertRaisesRegex(ValueError, "both used less often"):
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
        self.assertIn("Plan summary", page)
        self.assertIn("Edit settings", page)
        self.assertIn("Your weekly plan", page)
        self.assertIn("Total range:</strong> CAD$53.32 to CAD$75.30", page)
        self.assertIn('class="budget-status good"', page)
        self.assertIn('class="budget-status good"', page)
        self.assertIn('<summary>Meal guidance</summary>', page)
        self.assertIn('<summary>Budget + estimated prices</summary>', page)
        self.assertIn('<summary>Pantry items from home</summary>', page)
        self.assertIn('<table class="estimate-table">', page)
        self.assertIn("<th>Estimated range</th>", page)
        shopping_section = page.split(
            '<section class="shopping-list">',
            1,
        )[1].split("<h3>Estimated price ranges</h3>", 1)[0]
        self.assertNotIn("estimated range", shopping_section.casefold())
        self.assertIn("local planning estimate range only", page)
        self.assertIn("Tell us the minimum. You can customize more if you want.", page)
        self.assertIn("Plan your week", page)
        self.assertIn("Target grocery budget", page)
        self.assertIn("Pantry", page)
        self.assertIn("Dietary needs", page)
        self.assertIn("Used only to compare the simulated plan estimate with your target.", page)
        self.assertIn("No request is sent to Instacart", page)
        self.assertIn("Food rules", page)
        self.assertIn("Foods to avoid", page)
        self.assertIn("Food rules applied:", page)
        self.assertNotIn("Foods to use less often", page)
        self.assertNotIn("Foods to use more often", page)
        self.assertIn("Manage local meals and foods", page)
        self.assertIn(CSRF_TOKEN, page)
        self.assertIn('name="dietary_lactose_intolerance"', page)

    def test_initial_page_uses_neutral_quick_start_defaults(self) -> None:
        page = render_page()

        self.assertIn('value="2"', page)
        self.assertIn('value="4"', page)
        self.assertIn('value="normal" selected', page)
        self.assertIn("Food rules", page)
        self.assertNotIn('name="dietary_lactose_intolerance" checked', page)
        self.assertNotIn('name="dietary_vegetarian" checked', page)
        self.assertNotIn(">rice, 7 eggs</textarea>", page)

    def test_renders_portable_export_actions(self) -> None:
        page = render_page(_reference_form(), plan=create_plan(_reference_form()))

        self.assertIn('data-copy-target="plan-output"', page)
        self.assertIn("Print plan", page)
        self.assertIn('action="/download/plan"', page)
        self.assertIn('action="/download/instacart-paste-list"', page)
        self.assertIn('action="/download/instacart-json"', page)
        self.assertIn("@media print", page)
        self.assertIn("retailer-neutral Canadian price catalogue", page)
        self.assertIn("Food rules applied:", page)
        self.assertIn("Lactose intolerance", page)

    def test_plan_route_handles_get_requests_without_404(self) -> None:
        server = ThreadingHTTPServer((HOST, 0), CarrinhoHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://{HOST}:{server.server_address[1]}"
            plan_body = ""
            for path, expected in (("/plan", "Plan your week"), ("/plan/", "Plan your week"), ("/customize/", "Local catalogue JSON")):
                with self.subTest(path=path):
                    request = Request(f"{base_url}{path}", method="GET")
                    with urlopen(request, timeout=5) as response:
                        body = response.read().decode("utf-8")
                    self.assertEqual(response.status, 200)
                    self.assertIn(expected, body)
                    self.assertNotIn("Page not found.", body)
                    if path == "/plan":
                        plan_body = body
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertIn("Plan your week", plan_body)
        self.assertIn("Create my meal plan", plan_body)

    def test_renders_progressive_meal_review_sections(self) -> None:
        page = render_page(_reference_form(), plan=create_plan(_reference_form()))

        self.assertIn("Weekly overview", page)
        self.assertIn("Expand all", page)
        self.assertIn('data-expand-all="meal-details"', page)
        self.assertIn('aria-expanded="false"', page)
        self.assertIn('data-label-collapsed="Open details"', page)
        self.assertIn('class="meal-card"', page)
        self.assertIn("Meal guidance", page)
        self.assertIn("Shopping list", page)
        self.assertIn("Pantry", page)
        self.assertIn("Check + quantity", page)
        self.assertIn('id="pantry_transcript"', page)
        self.assertIn('type="checkbox"', page)
        self.assertIn("Audio transcript or spoken note", page)
        self.assertIn("overview-scroll", page)

    def test_renders_a_safe_local_catalogue_editor(self) -> None:
        content = '{"schema":"test","value":"</textarea><script>bad()</script>"}'

        page = render_customization_page(
            content,
            message="Saved locally.",
            error="Example <error>.",
        )

        self.assertIn("Local catalogue JSON", page)
        self.assertIn("Saved locally.", page)
        self.assertIn("Example &lt;error&gt;.", page)
        self.assertNotIn("</textarea><script>bad()</script>", page)
        self.assertIn("Restore latest backup", page)
        self.assertIn("my_rice_bowl", page)
        self.assertIn("Frozen spinach", page)
        self.assertIn(CSRF_TOKEN, page)

    def test_serves_plan_and_shopping_list_downloads_locally(self) -> None:
        server = ThreadingHTTPServer((HOST, 0), CarrinhoHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://{HOST}:{server.server_address[1]}"
            form = _reference_form()
            form["csrf_token"] = CSRF_TOKEN

            plan_response = _post_form(base_url, "/download/plan", form)
            paste_response = _post_form(
                base_url,
                "/download/instacart-paste-list",
                form,
            )
            json_response = _post_form(base_url, "/download/instacart-json", form)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertIn("MEAL PLAN", plan_response.body)
        self.assertIn("Estimated total range: CAD$53.32 to CAD$75.30", plan_response.body)
        self.assertEqual(
            plan_response.content_disposition,
            'attachment; filename="meal-plan.txt"',
        )
        self.assertIn("chicken thighs (1.2 kg)", paste_response.body)
        self.assertEqual(
            paste_response.content_disposition,
            'attachment; filename="instacart-paste-list.txt"',
        )
        self.assertIn('"link_type": "shopping_list"', json_response.body)
        self.assertEqual(json_response.content_type, "application/json; charset=utf-8")


class _LocalResponse:
    def __init__(
        self,
        body: str,
        content_type: str | None,
        content_disposition: str | None,
    ) -> None:
        self.body = body
        self.content_type = content_type
        self.content_disposition = content_disposition


def _post_form(
    base_url: str,
    path: str,
    values: dict[str, str],
) -> _LocalResponse:
    request = Request(
        f"{base_url}{path}",
        data=urlencode(values).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return _LocalResponse(
            response.read().decode("utf-8"),
            response.headers.get("Content-Type"),
            response.headers.get("Content-Disposition"),
        )


if __name__ == "__main__":
    unittest.main()
