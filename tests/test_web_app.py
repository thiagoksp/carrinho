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
        self.assertIn("Your Carrinho plan", page)
        self.assertIn("Estimated total: CAD$58.25", page)
        self.assertIn("No request is sent to Instacart", page)
        self.assertIn("Foods to use less often", page)
        self.assertIn("Longer plans may still include", page)
        self.assertIn("Manage local meals and foods", page)
        self.assertIn(CSRF_TOKEN, page)

    def test_renders_portable_export_actions(self) -> None:
        page = render_page(_reference_form(), plan=create_plan(_reference_form()))

        self.assertIn('data-copy-target="plan-output"', page)
        self.assertIn("Print plan", page)
        self.assertIn('action="/download/plan"', page)
        self.assertIn('action="/download/instacart-paste-list"', page)
        self.assertIn('action="/download/instacart-json"', page)
        self.assertIn("@media print", page)
        self.assertIn("retailer-neutral Canadian price catalogue", page)

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
        self.assertIn("Estimated total: CAD$58.25", plan_response.body)
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
