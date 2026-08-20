import re
import unittest

from meal_catalogue import load_default_meal_catalogue
from planning import generate_plan
from app import format_plan
from request_parser import parse_request


class TestRecipeGuidance(unittest.TestCase):
    def test_templates_contain_ingredients_and_steps(self) -> None:
        catalogue = load_default_meal_catalogue()
        # Check at least one template has 3-6 steps and ingredients
        found = False
        for tmpl in catalogue.templates:
            if tmpl.instructions and 3 <= len(tmpl.instructions) <= 6 and tmpl.ingredients:
                found = True
                # also ensure ingredient entries have expected attributes
                for ing in tmpl.ingredients:
                    assert hasattr(ing, 'product_key')
                    assert hasattr(ing, 'quantity_per_person')
                    assert hasattr(ing, 'planning_unit')
                break
        self.assertTrue(found, "No template with 3-6 instructions and ingredients found in catalogue")

    def test_format_plan_renders_ingredients_and_steps(self) -> None:
        request_text = (
            "I have CAD$80 to feed 4 people for 2 days. We have normal energy and no pantry items."
        )
        plan = generate_plan(parse_request(request_text))
        assert plan is not None
        content = format_plan(plan)
        # Ingredients header should appear for at least one meal
        self.assertRegex(content, r"Ingredients \(for 4 people\):")
        # Steps header and numbered step should appear
        self.assertIn("Steps:", content)
        self.assertRegex(content, r"\n\s*\d+\. \w+", "Numbered steps expected")
        # Check for at least one common ingredient keyword
        self.assertRegex(content.lower(), r"\b(rice|ground beef|eggs|tomato|chicken)\b")


if __name__ == "__main__":
    unittest.main()
