import json
from pathlib import Path
import tempfile
import unittest

from integrations import load_integrations, load_pilot_integration


def _valid_record() -> dict[str, object]:
    return {
        "id": "no-frills-toronto",
        "pilot_store": "No Frills",
        "pilot_location": "Toronto, ON",
        "country": "CA",
        "currency": "CAD",
        "price_source": "simulated",
        "price_status": "available",
        "local_catalog": "simulated-prices.json",
        "list_delivery": "instacart",
        "delivery_status": "planned",
        "supports_store_selection": False,
        "real_prices_available": False,
        "notice": "Only one simulated price source is active.",
    }


def _valid_catalog(
    currency: str = "CAD", catalog_type: str = "simulated"
) -> dict[str, object]:
    return {
        "currency": currency,
        "price_type": catalog_type,
        "description": "Temporary catalog for tests.",
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
            }
        ],
    }


def _save_temporary_registry(
    records: list[dict[str, object]],
    directory: str,
    catalog: dict[str, object] | None = None,
) -> Path:
    catalog_path = Path(directory) / "simulated-prices.json"
    catalog_path.write_text(
        json.dumps(catalog or _valid_catalog()),
        encoding="utf-8",
    )
    registry_path = Path(directory) / "integrations.json"
    registry_path.write_text(
        json.dumps({"integrations": records}),
        encoding="utf-8",
    )
    return registry_path


class TestIntegrations(unittest.TestCase):
    def test_loads_no_frills_as_the_planned_pilot(self) -> None:
        pilot = load_pilot_integration()

        self.assertEqual(pilot.pilot_store, "No Frills")
        self.assertEqual(pilot.pilot_location, "Toronto, ON")
        self.assertEqual(pilot.list_delivery, "instacart")
        self.assertEqual(pilot.price_status, "available")
        self.assertEqual(pilot.delivery_status, "planned")
        self.assertFalse(pilot.supports_store_selection)
        self.assertEqual(pilot.local_catalog.name, "simulated-prices.json")
        self.assertFalse(pilot.can_deliver_list)
        self.assertFalse(pilot.can_use_real_prices)

    def test_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = _save_temporary_registry(
                [_valid_record(), _valid_record()], directory
            )

            with self.assertRaisesRegex(ValueError, "duplicate integration ids"):
                load_integrations(path)

    def test_rejects_invalid_control_values(self) -> None:
        cases = (
            ("price_source", "hidden-site", "invalid price source"),
            ("list_delivery", "scraping", "invalid list delivery"),
            ("price_status", "ready", "invalid price status"),
            ("delivery_status", "ready", "invalid delivery status"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                record = _valid_record()
                record[field] = value
                with tempfile.TemporaryDirectory() as directory:
                    path = _save_temporary_registry([record], directory)
                    with self.assertRaisesRegex(ValueError, message):
                        load_integrations(path)

    def test_rejects_multiple_or_comparison_price_source_fields(self) -> None:
        for extra_field in ("price_sources", "comparison_sources"):
            with self.subTest(field=extra_field):
                record = _valid_record()
                record[extra_field] = ["simulated", "another-store"]
                with tempfile.TemporaryDirectory() as directory:
                    path = _save_temporary_registry([record], directory)
                    with self.assertRaisesRegex(ValueError, "unsupported fields"):
                        load_integrations(path)

    def test_rejects_real_prices_without_a_licensed_source(self) -> None:
        record = _valid_record()
        record["real_prices_available"] = True

        with tempfile.TemporaryDirectory() as directory:
            path = _save_temporary_registry([record], directory)

            with self.assertRaisesRegex(ValueError, "one licensed price source"):
                load_integrations(path)

    def test_rejects_real_prices_from_a_planned_source(self) -> None:
        record = _valid_record()
        record["price_source"] = "licensed"
        record["price_status"] = "planned"
        record["real_prices_available"] = True

        with tempfile.TemporaryDirectory() as directory:
            path = _save_temporary_registry(
                [record], directory, _valid_catalog(catalog_type="licensed")
            )

            with self.assertRaisesRegex(ValueError, "available price source"):
                load_integrations(path)

    def test_rejects_a_simulated_catalog_as_a_licensed_source(self) -> None:
        record = _valid_record()
        record["price_source"] = "licensed"
        record["price_status"] = "available"
        record["real_prices_available"] = True

        with tempfile.TemporaryDirectory() as directory:
            path = _save_temporary_registry([record], directory)

            with self.assertRaisesRegex(ValueError, "labelled as licensed"):
                load_integrations(path)

    def test_instacart_cannot_promise_a_specific_store(self) -> None:
        record = _valid_record()
        record["supports_store_selection"] = True

        with tempfile.TemporaryDirectory() as directory:
            path = _save_temporary_registry([record], directory)

            with self.assertRaisesRegex(ValueError, "cannot guarantee"):
                load_integrations(path)

    def test_validates_the_local_catalog_boundary(self) -> None:
        cases = (
            ("missing.json", _valid_catalog(), "does not exist"),
            ("../prices.json", _valid_catalog(), "outside the data directory"),
            (
                "simulated-prices.json",
                _valid_catalog(catalog_type="real"),
                "labelled as simulated",
            ),
            (
                "simulated-prices.json",
                _valid_catalog(currency="USD"),
                "another currency",
            ),
        )
        for catalog_path, catalog, message in cases:
            with self.subTest(path=catalog_path, message=message):
                record = _valid_record()
                record["local_catalog"] = catalog_path
                with tempfile.TemporaryDirectory() as directory:
                    path = _save_temporary_registry([record], directory, catalog)
                    with self.assertRaisesRegex(ValueError, message):
                        load_integrations(path)


if __name__ == "__main__":
    unittest.main()
