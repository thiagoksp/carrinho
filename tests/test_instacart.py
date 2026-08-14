from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest

from instacart import (
    create_instacart_paste_list,
    create_instacart_payload,
    save_instacart_paste_list,
    save_instacart_payload,
    serialize_instacart_payload,
)
from planning import generate_plan
from request_parser import ParsedRequest


def _base_plan(pantry_items: list[str] | None = None):
    request_data = ParsedRequest(
        budget=100,
        currency="CAD",
        people=2,
        days=4,
        cooking_energy="low",
        pantry_items=pantry_items if pantry_items is not None else [],
        dietary_restrictions=[],
        shopping_location="Toronto",
        selected_store="No Frills",
    )
    plan = generate_plan(request_data)
    assert plan is not None
    return plan


class TestInstacart(unittest.TestCase):
    def test_creates_minimal_payload_with_structured_measurements(self) -> None:
        plan = _base_plan(["rice", "7 eggs"])

        payload = create_instacart_payload(plan)

        self.assertEqual(payload["link_type"], "shopping_list")
        self.assertEqual(len(payload["line_items"]), len(plan.shopping_items))
        items = {item["name"]: item for item in payload["line_items"]}
        self.assertEqual(
            items["chicken thighs"]["line_item_measurements"],
            [{"quantity": 1.2, "unit": "kg"}],
        )
        self.assertEqual(
            items["tomato sauce"]["line_item_measurements"],
            [{"quantity": 2, "unit": "can"}],
        )
        self.assertEqual(
            items["canned beans"]["line_item_measurements"],
            [{"quantity": 3, "unit": "can"}],
        )
        self.assertEqual(
            items["vegetable oil"]["line_item_measurements"],
            [{"quantity": 946, "unit": "ml"}],
        )

    def test_converts_eggs_to_each_and_rice_to_kilograms(self) -> None:
        payload = create_instacart_payload(_base_plan([]))
        items = {item["name"]: item for item in payload["line_items"]}

        self.assertEqual(
            items["large eggs"]["line_item_measurements"],
            [{"quantity": 12, "unit": "each"}],
        )
        self.assertEqual(
            items["rice"]["line_item_measurements"],
            [{"quantity": 2, "unit": "kg"}],
        )

    def test_omits_prices_store_location_and_secrets(self) -> None:
        payload = create_instacart_payload(_base_plan(["rice", "7 eggs"]))
        serialized = json.dumps(payload, ensure_ascii=False)

        for item in payload["line_items"]:
            self.assertNotIn("quantity", item)
            self.assertNotIn("unit", item)
        for forbidden_text in (
            "price",
            "budget",
            "CAD$",
            "Toronto",
            "No Frills",
            "Authorization",
            "api_key",
            "country_code",
        ):
            self.assertNotIn(forbidden_text, serialized)

    def test_rejects_empty_list_and_invalid_measurements(self) -> None:
        plan = _base_plan(["rice", "7 eggs"])
        with self.assertRaisesRegex(ValueError, "no shopping items"):
            create_instacart_payload(replace(plan, shopping_items=()))

        item = plan.shopping_items[0]
        cases = (
            (replace(item, instacart_quantity=0), "greater than zero"),
            (replace(item, instacart_quantity=math.nan), "finite"),
            (replace(item, instacart_unit="dozen"), "Unsupported"),
            (replace(item, instacart_search_term=""), "search term"),
        )
        for invalid_item, message in cases:
            with self.subTest(message=message):
                invalid_plan = replace(plan, shopping_items=(invalid_item,))
                with self.assertRaisesRegex(ValueError, message):
                    create_instacart_payload(invalid_plan)

    def test_serializes_readable_json_and_saves_without_overwriting(self) -> None:
        plan = _base_plan(["rice", "7 eggs"])
        serialized = serialize_instacart_payload(plan)

        self.assertIn("Carrinho list — 2 people for 4 days", serialized)
        self.assertEqual(json.loads(serialized)["link_type"], "shopping_list")

        with tempfile.TemporaryDirectory() as directory:
            first = save_instacart_payload(plan, Path(directory))
            second = save_instacart_payload(plan, Path(directory))

            self.assertEqual(first.name, "instacart-list.json")
            self.assertEqual(second.name, "instacart-list-2.json")
            self.assertEqual(
                json.loads(first.read_text(encoding="utf-8")),
                json.loads(second.read_text(encoding="utf-8")),
            )

    def test_creates_text_list_for_manual_pasting(self) -> None:
        plan = _base_plan(["rice", "7 eggs"])

        paste_list = create_instacart_paste_list(plan)

        lines = paste_list.splitlines()
        self.assertEqual(len(lines), len(plan.shopping_items))
        self.assertIn("chicken thighs (1.2 kg)", lines)
        self.assertIn("tomato sauce (2 cans)", lines)
        self.assertIn("vegetable oil (946 ml)", lines)
        self.assertNotIn("Toronto", paste_list)
        self.assertNotIn("No Frills", paste_list)
        self.assertNotIn("CAD$", paste_list)

    def test_paste_list_enforces_limit_and_does_not_overwrite(self) -> None:
        plan = _base_plan(["rice", "7 eggs"])
        items_at_limit = tuple(plan.shopping_items[0] for _ in range(200))
        too_many_items = tuple(plan.shopping_items[0] for _ in range(201))

        self.assertEqual(
            len(
                create_instacart_paste_list(
                    replace(plan, shopping_items=items_at_limit)
                ).splitlines()
            ),
            200,
        )
        with self.assertRaisesRegex(ValueError, "no more than 200 items"):
            create_instacart_paste_list(
                replace(plan, shopping_items=too_many_items)
            )

        with tempfile.TemporaryDirectory() as directory:
            first = save_instacart_paste_list(plan, Path(directory))
            second = save_instacart_paste_list(plan, Path(directory))

            self.assertEqual(first.name, "instacart-paste-list.txt")
            self.assertEqual(second.name, "instacart-paste-list-2.txt")
            self.assertEqual(
                first.read_text(encoding="utf-8"),
                second.read_text(encoding="utf-8"),
            )

    def test_paste_list_rejects_separators_and_control_characters(self) -> None:
        plan = _base_plan(["rice", "7 eggs"])
        item = plan.shopping_items[0]

        for search_term in (
            "chicken thighs, ice cream",
            "chicken thighs\nice cream",
            "chicken thighs\rice cream",
            "chicken thighs\u2028ice cream",
            "chicken thighs\u0000ice cream",
        ):
            with self.subTest(search_term=repr(search_term)):
                invalid_item = replace(item, instacart_search_term=search_term)
                with self.assertRaisesRegex(
                    ValueError,
                    "separators or control characters",
                ):
                    create_instacart_paste_list(
                        replace(plan, shopping_items=(invalid_item,))
                    )

    def test_paste_list_validates_items_and_formats_units(self) -> None:
        plan = _base_plan([])
        items = {item.instacart_search_term: item for item in plan.shopping_items}
        paste_list = create_instacart_paste_list(plan).splitlines()

        self.assertIn("large eggs (12)", paste_list)
        self.assertIn("potatoes (5 lb bag)", paste_list)
        self.assertIn("all-purpose seasoning (1 package)", paste_list)
        with self.assertRaisesRegex(ValueError, "no shopping items"):
            create_instacart_paste_list(replace(plan, shopping_items=()))

        cases = (
            replace(items["large eggs"], instacart_quantity=0),
            replace(items["large eggs"], instacart_unit="dozen"),
            replace(items["large eggs"], instacart_search_term=""),
        )
        for invalid_item in cases:
            with self.subTest(item=invalid_item):
                with self.assertRaises(ValueError):
                    create_instacart_paste_list(
                        replace(plan, shopping_items=(invalid_item,))
                    )


if __name__ == "__main__":
    unittest.main()
