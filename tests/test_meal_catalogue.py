import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from catalog import load_simulated_catalog
from meal_catalogue import MEAL_CATALOGUE_SCHEMA, load_default_meal_catalogue, load_meal_catalogue


class TestMealCatalogue(unittest.TestCase):
    def test_loads_the_versioned_default_catalogue(self) -> None:
        catalogue = load_default_meal_catalogue()

        self.assertEqual(len(catalogue.templates), 22)
        self.assertEqual(
            catalogue.templates[0].key,
            "roasted_chicken_rice_vegetables",
        )
        self.assertEqual(
            catalogue.templates[0].ingredients[0].product_key,
            "chicken",
        )
        self.assertEqual(
            catalogue.templates[0].ingredients[0].planning_unit,
            "g",
        )
        self.assertEqual(catalogue.templates[0].cooking_energy, "normal")
        self.assertEqual(catalogue.templates[0].dietary_tags, ("lactose-free",))
        self.assertEqual(catalogue.templates[0].catalogue_tier, "core")
        self.assertIn("batch-friendly", catalogue.templates[0].selection_tags)
        self.assertEqual(
            [template.catalogue_tier for template in catalogue.templates].count("core"),
            10,
        )
        self.assertEqual(
            {
                template.cuisine
                for template in catalogue.templates
            },
            {
                "east-asian",
                "global",
                "indian",
                "mediterranean",
                "mexican",
                "middle-eastern",
                "south-american",
            },
        )

    def test_uses_product_keys_and_units_shared_with_the_price_catalog(self) -> None:
        catalogue = load_default_meal_catalogue()
        products = {
            product.key: product for product in load_simulated_catalog().products
        }

        for template in catalogue.templates:
            for ingredient in template.ingredients:
                self.assertIn(ingredient.product_key, products)
                self.assertEqual(
                    ingredient.planning_unit,
                    products[ingredient.product_key].planning_unit,
                )

    def test_rejects_an_unknown_schema(self) -> None:
        data = self._valid_data()
        data["schema"] = "unknown"

        with self.assertRaisesRegex(ValueError, "unsupported schema"):
            self._load_data(data)

    def test_rejects_duplicate_template_keys(self) -> None:
        data = self._valid_data()
        data["templates"].append(data["templates"][0])

        with self.assertRaisesRegex(ValueError, "duplicate template keys"):
            self._load_data(data)

    def test_rejects_invalid_ingredient_units_and_quantities(self) -> None:
        data = self._valid_data()
        ingredient = data["templates"][0]["ingredients"][0]
        ingredient["planning_unit"] = "lb"

        with self.assertRaisesRegex(ValueError, "unsupported planning unit"):
            self._load_data(data)

        ingredient["planning_unit"] = "g"
        ingredient["quantity_per_person"] = 0
        with self.assertRaisesRegex(ValueError, "invalid quantity per person"):
            self._load_data(data)

    def test_rejects_unsupported_meal_selection_metadata(self) -> None:
        data = self._valid_data()
        data["templates"][0]["cooking_energy"] = "very low"

        with self.assertRaisesRegex(ValueError, "unsupported cooking energy"):
            self._load_data(data)

        data = self._valid_data()
        data["templates"][0]["dietary_tags"] = ["gluten-free"]
        with self.assertRaisesRegex(ValueError, "unsupported dietary tags"):
            self._load_data(data)

        data = self._valid_data()
        data["templates"][0]["catalogue_tier"] = "experimental"
        with self.assertRaisesRegex(ValueError, "unsupported catalogue tier"):
            self._load_data(data)

        data = self._valid_data()
        data["templates"][0]["selection_tags"] = ["cheap"]
        with self.assertRaisesRegex(ValueError, "unsupported selection tags"):
            self._load_data(data)

        data = self._valid_data()
        for template in data["templates"]:
            template["catalogue_tier"] = "extended"
        with self.assertRaisesRegex(ValueError, "at least one core template"):
            self._load_data(data)

    def _valid_data(self) -> dict[str, object]:
        path = Path(__file__).resolve().parents[1] / "data" / "meal-catalogue.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_data(self, data: dict[str, object]) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "meal-catalogue.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            load_meal_catalogue(path)


if __name__ == "__main__":
    unittest.main()
