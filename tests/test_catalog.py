from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from catalog import PriceCatalog, load_catalog, load_simulated_catalog
from planning import generate_plan
from request_parser import ParsedRequest


class TestCatalog(unittest.TestCase):
    def test_loads_simulated_catalog_with_metadata(self) -> None:
        catalog = load_simulated_catalog()

        self.assertEqual(catalog.currency, "CAD")
        self.assertEqual(catalog.price_type, "simulated")
        self.assertIn("do not represent current offers", catalog.description)
        self.assertEqual(len(catalog.products), 13)
        self.assertTrue(
            all(product.package_price >= 0 for product in catalog.products)
        )

    def test_rejects_duplicate_product_keys(self) -> None:
        data = {
            "currency": "CAD",
            "price_type": "test",
            "description": "Invalid test catalog.",
            "products": [
                {
                    "key": "rice",
                    "name": "Rice",
                    "package_description": "1 kg",
                    "package_size": 1,
                    "package_price": 5,
                    "keywords": ["rice"],
                    "instacart_search_term": "rice",
                    "instacart_quantity": 1,
                    "instacart_unit": "kg",
                },
                {
                    "key": "rice",
                    "name": "Other rice",
                    "package_description": "2 kg",
                    "package_size": 2,
                    "package_price": 8,
                    "keywords": ["rice"],
                    "instacart_search_term": "rice",
                    "instacart_quantity": 2,
                    "instacart_unit": "kg",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate product keys"):
                load_catalog(path)

    def test_generator_accepts_another_catalog_without_changing_rules(self) -> None:
        original = load_simulated_catalog()
        higher_priced_products = tuple(
            replace(
                product,
                package_price=product.package_price * 2,
            )
            for product in original.products
        )
        catalog = PriceCatalog(
            currency="CAD",
            price_type="test",
            description="Doubled prices for testing.",
            products=higher_priced_products,
        )
        request = ParsedRequest(
            budget=1000,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["rice", "7 eggs"],
            dietary_restrictions=[],
        )

        plan = generate_plan(request, catalog)

        assert plan is not None
        self.assertEqual(plan.estimated_total, 116.50)
        self.assertEqual(plan.price_type, "test")
        self.assertEqual(plan.price_description, "Doubled prices for testing.")

    def test_rejects_catalog_missing_a_required_product(self) -> None:
        original = load_simulated_catalog()
        incomplete_catalog = replace(
            original,
            products=tuple(
                product
                for product in original.products
                if product.key != "rice"
            ),
        )
        request = ParsedRequest(
            budget=1000,
            currency="CAD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["7 eggs"],
            dietary_restrictions=[],
        )

        with self.assertRaisesRegex(
            ValueError,
            "does not contain prices for: rice",
        ):
            generate_plan(request, incomplete_catalog)

    def test_plan_uses_the_catalog_currency(self) -> None:
        original = load_simulated_catalog()
        usd_catalog = replace(original, currency="USD")
        request = ParsedRequest(
            budget=1000,
            currency="USD",
            people=2,
            days=4,
            cooking_energy="low",
            pantry_items=["rice", "7 eggs"],
            dietary_restrictions=[],
        )

        plan = generate_plan(request, usd_catalog)

        assert plan is not None
        self.assertEqual(plan.currency, "USD")
        self.assertEqual(plan.estimated_total, 58.25)

    def test_rejects_non_finite_numbers_and_empty_keywords(self) -> None:
        cases = (
            ("package_size", float("nan"), "invalid quantity or price"),
            ("package_price", float("inf"), "invalid quantity or price"),
            ("instacart_quantity", 0, "invalid quantity or price"),
            ("keywords", [""], "requires at least one keyword"),
            ("instacart_unit", "dozen", "unsupported Instacart unit"),
        )
        for field, value, message in cases:
            with self.subTest(field=field, value=value):
                data = {
                    "currency": "CAD",
                    "price_type": "test",
                    "description": "Invalid test catalog.",
                    "products": [
                        {
                            "key": "rice",
                            "name": "Rice",
                            "package_description": "1 kg",
                            "package_size": 1,
                            "package_price": 5,
                            "keywords": ["rice"],
                            "instacart_search_term": "rice",
                            "instacart_quantity": 1,
                            "instacart_unit": "kg",
                            field: value,
                        }
                    ],
                }

                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "catalog.json"
                    path.write_text(json.dumps(data), encoding="utf-8")

                    with self.assertRaisesRegex(ValueError, message):
                        load_catalog(path)


if __name__ == "__main__":
    unittest.main()
