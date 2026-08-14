import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from household_profile import (
    HOUSEHOLD_PROFILE_SCHEMA,
    HouseholdProfile,
    apply_household_defaults,
    load_household_profile,
    save_household_profile,
)
from request_parser import ParsedRequest


def _request() -> ParsedRequest:
    return ParsedRequest(
        budget=80,
        currency="CAD",
        people=2,
        days=4,
        cooking_energy="low",
        pantry_items=["rice", "7 eggs"],
        dietary_restrictions=["lactose intolerance"],
        avoided_product_keys=["onions"],
        preferred_product_keys=["chicken", "eggs"],
    )


class TestHouseholdProfile(unittest.TestCase):
    def test_saves_only_private_household_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            path = save_household_profile(_request(), Path(directory))
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema"], HOUSEHOLD_PROFILE_SCHEMA)
        self.assertEqual(data["people"], 2)
        self.assertEqual(data["pantry_items"], ["rice", "7 eggs"])
        self.assertEqual(data["avoided_product_keys"], ["onions"])
        self.assertEqual(data["preferred_product_keys"], ["chicken", "eggs"])
        self.assertNotIn("budget", data)
        self.assertNotIn("days", data)
        self.assertNotIn("currency", data)

    def test_loads_an_existing_household_profile(self) -> None:
        with TemporaryDirectory() as directory:
            save_household_profile(_request(), Path(directory))
            profile = load_household_profile(Path(directory))

        self.assertEqual(
            profile,
            HouseholdProfile(
                people=2,
                cooking_energy="low",
                pantry_items=("rice", "7 eggs"),
                dietary_restrictions=("lactose intolerance",),
                avoided_product_keys=("onions",),
                preferred_product_keys=("chicken", "eggs"),
            ),
        )

    def test_replaces_the_profile_only_after_the_caller_saves_again(self) -> None:
        request_data = _request()
        with TemporaryDirectory() as directory:
            path = save_household_profile(request_data, Path(directory))
            request_data.people = 3
            request_data.pantry_items = ["1 kg of rice"]
            updated_path = save_household_profile(request_data, Path(directory))
            profile = load_household_profile(Path(directory))

        self.assertEqual(path, updated_path)
        assert profile is not None
        self.assertEqual(profile.people, 3)
        self.assertEqual(profile.pantry_items, ("1 kg of rice",))

    def test_applies_defaults_without_overriding_current_request_data(self) -> None:
        request_data = ParsedRequest(budget=60, currency="CAD", people=4)
        profile = HouseholdProfile(
            people=2,
            cooking_energy="low",
            pantry_items=("rice", "7 eggs"),
            dietary_restrictions=("lactose intolerance",),
            avoided_product_keys=("beans",),
            preferred_product_keys=("eggs",),
        )

        result = apply_household_defaults(request_data, profile)

        self.assertEqual(result.people, 4)
        self.assertEqual(result.cooking_energy, "low")
        self.assertEqual(result.pantry_items, ["rice", "7 eggs"])
        self.assertEqual(result.dietary_restrictions, ["lactose intolerance"])
        self.assertEqual(result.avoided_product_keys, ["beans"])
        self.assertEqual(result.preferred_product_keys, ["eggs"])

    def test_loads_a_legacy_profile_with_empty_food_preferences(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "household-profile.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": "carrinho.household-profile.v1",
                        "people": 2,
                        "cooking_energy": "low",
                        "pantry_items": ["rice"],
                        "dietary_restrictions": [],
                    }
                ),
                encoding="utf-8",
            )
            profile = load_household_profile(Path(directory))

        assert profile is not None
        self.assertEqual(profile.avoided_product_keys, ())
        self.assertEqual(profile.preferred_product_keys, ())

    def test_rejects_unknown_or_conflicting_product_preference_keys(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "household-profile.json"
            base_data = {
                "schema": HOUSEHOLD_PROFILE_SCHEMA,
                "people": 2,
                "cooking_energy": "low",
                "pantry_items": [],
                "dietary_restrictions": [],
                "avoided_product_keys": ["mushrooms"],
                "preferred_product_keys": [],
            }
            path.write_text(json.dumps(base_data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown product preference"):
                load_household_profile(Path(directory))

            base_data["avoided_product_keys"] = ["eggs"]
            base_data["preferred_product_keys"] = ["eggs"]
            path.write_text(json.dumps(base_data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot avoid and prefer"):
                load_household_profile(Path(directory))

    def test_rejects_corrupt_or_unsupported_profile_data(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "household-profile.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "could not be read"):
                load_household_profile(Path(directory))

            path.write_text(
                json.dumps({"schema": "unknown"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unsupported schema"):
                load_household_profile(Path(directory))


if __name__ == "__main__":
    unittest.main()
