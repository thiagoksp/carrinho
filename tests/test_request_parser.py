import unittest

from request_parser import parse_request


BASE_CASE = (
    "I have CAD$80 to feed 2 people for 4 days. "
    "We have low energy for cooking, already have enough rice and 7 eggs, "
    "and at least one person is lactose intolerant. We need lunch and dinner."
)


class TestRequestParser(unittest.TestCase):
    def test_identifies_the_base_case_data(self) -> None:
        request = parse_request(BASE_CASE)

        self.assertEqual(request.budget, 80)
        self.assertEqual(request.currency, "CAD")
        self.assertEqual(request.people, 2)
        self.assertEqual(request.days, 4)
        self.assertEqual(request.cooking_energy, "low")
        self.assertEqual(request.pantry_items, ["enough rice", "7 eggs"])
        self.assertEqual(request.dietary_restrictions, ["lactose intolerance"])
        self.assertFalse(hasattr(request, "shopping_location"))
        self.assertFalse(hasattr(request, "selected_store"))

    def test_accepts_quantities_written_as_words(self) -> None:
        request = parse_request("I have CAD$50 for two people for three days.")

        self.assertEqual(request.people, 2)
        self.assertEqual(request.days, 3)

    def test_treats_a_bare_dollar_amount_as_canadian_dollars(self) -> None:
        request = parse_request("I have $80 for 2 people for 4 days.")

        self.assertEqual(request.budget, 80)
        self.assertEqual(request.currency, "CAD")

    def test_leaves_unreported_data_missing(self) -> None:
        request = parse_request("I need to organize my meals.")

        self.assertIsNone(request.budget)
        self.assertIsNone(request.people)
        self.assertIsNone(request.days)
        self.assertIsNone(request.cooking_energy)
        self.assertIsNone(request.pantry_items)
        self.assertIsNone(request.dietary_restrictions)
        self.assertFalse(hasattr(request, "shopping_location"))
        self.assertFalse(hasattr(request, "selected_store"))

    def test_ignores_location_and_retailer_as_planning_inputs(self) -> None:
        request = parse_request("I live in North York and I prefer No Frills.")

        self.assertFalse(hasattr(request, "shopping_location"))
        self.assertFalse(hasattr(request, "selected_store"))

    def test_retailer_context_does_not_change_other_request_data(self) -> None:
        request = parse_request(
            "I have CAD$80 for 2 people for 4 days. "
            "I am shopping in Toronto at No Frills."
        )

        self.assertEqual(request.budget, 80)
        self.assertEqual(request.currency, "CAD")
        self.assertEqual(request.people, 2)
        self.assertEqual(request.days, 4)
        self.assertFalse(hasattr(request, "shopping_location"))
        self.assertFalse(hasattr(request, "selected_store"))

    def test_location_and_retailer_context_does_not_pollute_pantry(self) -> None:
        request = parse_request(
            "I already have rice and 7 eggs; I live in Toronto, ON; "
            "I prefer No Frills."
        )

        self.assertEqual(request.pantry_items, ["rice", "7 eggs"])
        self.assertFalse(hasattr(request, "shopping_location"))
        self.assertFalse(hasattr(request, "selected_store"))

    def test_ignores_shopping_schedule_context(self) -> None:
        request = parse_request(
            "I have CAD$50 and want to shop on the weekend."
        )

        self.assertEqual(request.budget, 50)
        self.assertEqual(request.currency, "CAD")
        self.assertFalse(hasattr(request, "selected_store"))

    def test_cooking_preference_remains_retailer_neutral(self) -> None:
        request = parse_request("I have low energy for cooking and prefer not to cook.")

        self.assertEqual(request.cooking_energy, "low")
        self.assertFalse(hasattr(request, "selected_store"))

    def test_separates_fields_without_commas(self) -> None:
        request = parse_request(
            "I already have rice and 7 eggs and I live in Toronto "
            "and I prefer No Frills."
        )

        self.assertEqual(request.pantry_items, ["rice", "7 eggs"])
        self.assertFalse(hasattr(request, "shopping_location"))
        self.assertFalse(hasattr(request, "selected_store"))

    def test_no_store_preference_is_not_a_planning_field(self) -> None:
        request = parse_request(
            "I have CAD$80 and I have no store preference."
        )

        self.assertEqual(request.budget, 80)
        self.assertFalse(hasattr(request, "shopping_location"))
        self.assertFalse(hasattr(request, "selected_store"))

    def test_home_context_does_not_add_a_location_field(self) -> None:
        request = parse_request("I am at home with no energy for cooking.")

        self.assertEqual(request.cooking_energy, "low")
        self.assertFalse(hasattr(request, "shopping_location"))

    def test_distinguishes_no_items_from_missing_information(self) -> None:
        request = parse_request(
            "I have nothing at home and I have no dietary restrictions."
        )

        self.assertEqual(request.pantry_items, [])
        self.assertEqual(request.dietary_restrictions, [])

    def test_preserves_reported_pantry_quantities(self) -> None:
        request = parse_request(
            "I already have 1 kg of rice, half a package of pasta and 7 eggs."
        )

        self.assertEqual(
            request.pantry_items,
            ["1 kg of rice", "half a package of pasta", "7 eggs"],
        )


if __name__ == "__main__":
    unittest.main()
