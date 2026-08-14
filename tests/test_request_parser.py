import unittest

from request_parser import parse_request


BASE_CASE = (
    "I have CAD$80 to feed 2 people for 4 days. "
    "We have low energy for cooking, already have enough rice and 7 eggs, "
    "and at least one person is lactose intolerant. We need lunch and dinner. "
    "I am in Toronto and will shop at No Frills."
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
        self.assertEqual(request.shopping_location, "Toronto")
        self.assertEqual(request.selected_store, "No Frills")

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
        self.assertIsNone(request.shopping_location)
        self.assertIsNone(request.selected_store)

    def test_identifies_a_region_and_specific_store(self) -> None:
        request = parse_request("I live in North York and I prefer No Frills.")

        self.assertEqual(request.shopping_location, "North York")
        self.assertEqual(request.selected_store, "No Frills")

    def test_understands_shopping_location_and_store_phrasing(self) -> None:
        request = parse_request("I am shopping in Toronto at No Frills.")

        self.assertEqual(request.shopping_location, "Toronto")
        self.assertEqual(request.selected_store, "No Frills")

    def test_separates_pantry_location_and_store(self) -> None:
        request = parse_request(
            "I already have rice and 7 eggs; I live in Toronto, ON; "
            "I prefer No Frills."
        )

        self.assertEqual(request.pantry_items, ["rice", "7 eggs"])
        self.assertEqual(request.shopping_location, "Toronto, ON")
        self.assertEqual(request.selected_store, "No Frills")

    def test_does_not_treat_a_shopping_time_as_a_store(self) -> None:
        request = parse_request(
            "I have a budget in CAD and want to shop on the weekend."
        )

        self.assertIsNone(request.shopping_location)
        self.assertIsNone(request.selected_store)

    def test_does_not_treat_cooking_preference_as_a_store(self) -> None:
        request = parse_request("I have low energy and prefer not to cook.")

        self.assertIsNone(request.selected_store)

    def test_separates_fields_without_commas(self) -> None:
        request = parse_request(
            "I already have rice and 7 eggs and I live in Toronto "
            "and I prefer No Frills."
        )

        self.assertEqual(request.pantry_items, ["rice", "7 eggs"])
        self.assertEqual(request.shopping_location, "Toronto")
        self.assertEqual(request.selected_store, "No Frills")

    def test_no_store_preference_does_not_pollute_location(self) -> None:
        request = parse_request(
            "I am in Toronto and I have no store preference."
        )

        self.assertEqual(request.shopping_location, "Toronto")
        self.assertEqual(request.selected_store, "any store")

    def test_does_not_treat_being_at_home_as_a_location(self) -> None:
        request = parse_request("I am at home with no energy for cooking.")

        self.assertIsNone(request.shopping_location)

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
