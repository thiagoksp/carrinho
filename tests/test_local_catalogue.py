from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from local_catalogue import (
    LOCAL_CATALOGUE_SCHEMA,
    load_effective_meal_catalogue,
    load_effective_price_catalog,
    load_local_catalogue,
    read_local_catalogue_json,
    read_local_catalogue_source,
    restore_latest_local_catalogue,
    save_local_catalogue_json,
)
from planning import generate_plan
from request_parser import ParsedRequest


def _custom_product() -> dict[str, object]:
    return {
        "key": "spinach",
        "name": "Frozen spinach",
        "package_description": "300 g package",
        "package_size": 300,
        "package_price": 3.0,
        "planning_unit": "g",
        "variable_weight": False,
        "keywords": ["spinach"],
        "instacart_search_term": "frozen spinach",
        "instacart_quantity": 300,
        "instacart_unit": "g",
    }


def _custom_meal(product_key: str = "spinach") -> dict[str, object]:
    return {
        "key": "spinach_rice_bowl",
        "dish": "Spinach and rice bowl",
        "catalogue_tier": "extended",
        "cooking_energy": "low",
        "dietary_tags": ["lactose-free"],
        "selection_tags": ["quick", "one-pan"],
        "ingredients": [
            {
                "product_key": product_key,
                "quantity_per_person": 100,
                "planning_unit": "g",
            },
            {
                "product_key": "rice",
                "quantity_per_person": 100,
                "planning_unit": "g",
            },
        ],
    }


def _document(
    *,
    products: list[dict[str, object]] | None = None,
    meals: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps(
        {
            "schema": LOCAL_CATALOGUE_SCHEMA,
            "products": products or [],
            "meal_templates": meals or [],
        }
    )


class TestLocalCatalogue(unittest.TestCase):
    def test_absent_file_returns_an_empty_editable_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            local_directory = Path(directory)

            catalogue = load_local_catalogue(local_directory)
            content = read_local_catalogue_json(local_directory)

        self.assertEqual(catalogue.products, ())
        self.assertEqual(catalogue.meal_templates, ())
        self.assertEqual(json.loads(content)["schema"], LOCAL_CATALOGUE_SCHEMA)

    def test_saves_and_loads_validated_products_and_meals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            local_directory = Path(directory)
            result = save_local_catalogue_json(
                _document(products=[_custom_product()], meals=[_custom_meal()]),
                local_directory,
            )
            catalogue = load_local_catalogue(local_directory)

        self.assertEqual(result.product_count, 1)
        self.assertEqual(result.meal_template_count, 1)
        self.assertEqual(catalogue.products[0].key, "spinach")
        self.assertEqual(catalogue.meal_templates[0].key, "spinach_rice_bowl")

    def test_effective_catalogues_can_generate_a_plan_with_local_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            local_directory = Path(directory)
            save_local_catalogue_json(
                _document(products=[_custom_product()], meals=[_custom_meal()]),
                local_directory,
            )
            prices = load_effective_price_catalog(local_directory)
            meals = load_effective_meal_catalogue(local_directory)
            request = ParsedRequest(
                budget=80,
                currency="CAD",
                people=2,
                days=1,
                cooking_energy="low",
                pantry_items=[],
                dietary_restrictions=[],
                avoided_product_keys=[],
                preferred_product_keys=["spinach"],
            )
            plan = generate_plan(request, prices, meals)

        assert plan is not None
        self.assertEqual(plan.meals[0].dish, "Spinach and rice bowl")
        self.assertTrue(any(item.name == "Frozen spinach" for item in plan.shopping_items))

    def test_rejects_builtin_keys_unknown_products_and_wrong_units(self) -> None:
        duplicate_product = _custom_product()
        duplicate_product["key"] = "rice"
        cases = (
            _document(products=[duplicate_product]),
            _document(meals=[_custom_meal("unknown_food")]),
        )
        for content in cases:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as directory:
                    local_directory = Path(directory)
                    with self.assertRaises(ValueError):
                        save_local_catalogue_json(content, local_directory)
                    self.assertFalse(
                        (local_directory / "custom-catalogue.json").exists()
                    )

        wrong_unit_meal = _custom_meal()
        wrong_unit_meal["ingredients"][0]["planning_unit"] = "ml"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "wrong unit"):
                save_local_catalogue_json(
                    _document(
                        products=[_custom_product()],
                        meals=[wrong_unit_meal],
                    ),
                    Path(directory),
                )

    def test_invalid_update_preserves_the_previous_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            local_directory = Path(directory)
            first = _document(products=[_custom_product()])
            save_local_catalogue_json(first, local_directory)
            path = local_directory / "custom-catalogue.json"
            before = path.read_bytes()

            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                save_local_catalogue_json("{", local_directory)

            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((local_directory / "backups").exists())

    def test_rejects_retailer_fields_and_preserves_invalid_source_for_repair(self) -> None:
        product = _custom_product()
        product["retailer_sku"] = "private-123"
        with tempfile.TemporaryDirectory() as directory:
            local_directory = Path(directory)
            with self.assertRaisesRegex(ValueError, "unsupported fields"):
                save_local_catalogue_json(
                    _document(products=[product]),
                    local_directory,
                )

            path = local_directory / "custom-catalogue.json"
            path.write_text("{ broken", encoding="utf-8")
            self.assertEqual(
                read_local_catalogue_source(local_directory),
                "{ broken",
            )
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                read_local_catalogue_json(local_directory)

    def test_overwrite_creates_a_backup_and_restore_preserves_current_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            local_directory = Path(directory)
            first = _document(products=[_custom_product()])
            second = _document(
                products=[_custom_product()],
                meals=[_custom_meal()],
            )
            save_local_catalogue_json(first, local_directory)
            update = save_local_catalogue_json(
                second,
                local_directory,
                timestamp=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
            )
            restored = restore_latest_local_catalogue(
                local_directory,
                timestamp=datetime(2026, 8, 14, 12, 1, tzinfo=timezone.utc),
            )
            catalogue = load_local_catalogue(local_directory)

        assert update.backup_path is not None
        assert restored.backup_path is not None
        self.assertTrue(update.backup_path.name.endswith("120000000000Z.json"))
        self.assertEqual(restored.product_count, 1)
        self.assertEqual(restored.meal_template_count, 0)
        self.assertEqual(catalogue.meal_templates, ())


if __name__ == "__main__":
    unittest.main()
