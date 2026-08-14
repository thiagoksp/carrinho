import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from catalog import load_simulated_catalog
from integrations import load_pilot_integration
from manual_prices import (
    CSV_FIELDS,
    PriceImportErrors,
    create_csv_template,
    import_prices_csv,
    main,
)
from planning import generate_plan
from request_parser import parse_request


TODAY = date(2026, 8, 13)
NOW = datetime(2026, 8, 13, 15, 30, tzinfo=timezone.utc)
STORE_LOCATION = "No Frills - 345 Bloor St E, Toronto, ON"
BASE_CASE = (
    "I have CAD$80 to feed 2 people for 4 days. "
    "We have low energy for cooking, we already have rice and 7 eggs, "
    "and at least one person has lactose intolerance."
)


def _read_rows(
    path: Path, *, delimiter: str = ","
) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=delimiter))


def _save_rows(
    path: Path,
    rows: list[dict[str, str]],
    *,
    delimiter: str = ",",
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
            delimiter=delimiter,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


class TestManualPrices(unittest.TestCase):
    def _template(self, directory: str) -> Path:
        return create_csv_template(Path(directory) / "prices.csv")

    def _fill(
        self,
        path: Path,
        *,
        index: int = 0,
        observed_package: str = "750 g package",
        price: str = "CAD$13.49",
        observed_on: str = "2026-08-13",
        store_location: str = STORE_LOCATION,
        channel: str = "final-receipt",
        price_type: str = "regular",
        quantity_mode: str = "fixed-package",
        declared_source: str = "personal receipt without personal data",
        delimiter: str = ",",
    ) -> None:
        rows = _read_rows(path, delimiter=delimiter)
        rows[index].update(
            {
                "observed_package": observed_package,
                "price_cad": price,
                "observed_on": observed_on,
                "store_location": store_location,
                "channel": channel,
                "price_type": price_type,
                "quantity_mode": quantity_mode,
                "declared_source": declared_source,
            }
        )
        _save_rows(path, rows, delimiter=delimiter)

    def test_creates_excel_template_without_inventing_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prices.csv"
            first = create_csv_template(path)
            second = create_csv_template(path)
            rows = _read_rows(first)

            self.assertEqual(first.name, "prices.csv")
            self.assertEqual(second.name, "prices-2.csv")
            self.assertEqual(len(rows), 13)
            self.assertEqual(rows[0]["observed_package"], "")
            self.assertEqual(rows[0]["price_cad"], "")
            self.assertEqual(rows[0]["observed_on"], "")
            self.assertEqual(rows[0]["store_location"], "")
            self.assertEqual(rows[0]["channel"], "")
            self.assertEqual(rows[0]["price_type"], "")
            self.assertEqual(rows[0]["quantity_mode"], "")
            self.assertEqual(rows[0]["declared_source"], "")
            self.assertTrue(first.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_imports_self_declared_observation_with_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            self._fill(template)
            content = template.read_bytes()

            result = import_prices_csv(
                template, Path(directory), today=TODAY, now=NOW
            )
            snapshot = json.loads(result.path.read_text(encoding="utf-8"))
            observation = snapshot["observations"][0]

            self.assertEqual(result.count, 1)
            self.assertEqual(result.total_products, 13)
            self.assertEqual(
                snapshot["schema"],
                "carrinho.manual-price-observations.v3",
            )
            self.assertEqual(snapshot["type"], "manual-price-observations")
            self.assertEqual(snapshot["target_retailer"], "No Frills")
            self.assertEqual(snapshot["target_region"], "Toronto, ON")
            self.assertEqual(observation["observed_package"], "750 g package")
            self.assertEqual(observation["price_cents"], 1349)
            self.assertEqual(
                observation["declared_store_location"], STORE_LOCATION
            )
            self.assertEqual(observation["declared_channel"], "final-receipt")
            self.assertEqual(observation["declared_price_type"], "regular")
            self.assertEqual(
                observation["declared_quantity_mode"], "fixed-package"
            )
            self.assertEqual(
                observation["declared_source"],
                "personal receipt without personal data",
            )
            self.assertEqual(
                snapshot["source_file"]["sha256"],
                hashlib.sha256(content).hexdigest(),
            )
            self.assertIn("self-declared", snapshot["notice"])
            self.assertIn("cannot affect", snapshot["notice"])

    def test_accepts_simple_price_formats(self) -> None:
        formats = {
            "13.49": 1349,
            "13,49": 1349,
            "$13.49": 1349,
            "CAD$13.49": 1349,
            "cad$13.49": 1349,
        }
        for text, expected in formats.items():
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                self._fill(template, price=text)
                result = import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )
                data = json.loads(result.path.read_text(encoding="utf-8"))
                self.assertEqual(
                    data["observations"][0]["price_cents"], expected
                )

    def test_rejects_invalid_prices_without_creating_snapshot(self) -> None:
        invalid_values = (
            "",
            "0",
            "-1",
            "NaN",
            "inf",
            "5.999",
            "=5+1",
            "1,234.56",
            "1 3.49",
            "10000.01",
            "9" * 100,
        )
        for price in invalid_values:
            with self.subTest(price=price), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                self._fill(template, price=price)
                output = Path(directory) / "output"
                with self.assertRaises(PriceImportErrors):
                    import_prices_csv(
                        template, output, today=TODAY, now=NOW
                    )
                self.assertFalse(output.exists())

    def test_accepts_iso_and_excel_converted_dates(self) -> None:
        formats = ("2026-08-13", "8/13/2026")
        for text in formats:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                self._fill(template, observed_on=text)
                result = import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )
                data = json.loads(result.path.read_text(encoding="utf-8"))
                self.assertEqual(
                    data["observations"][0]["observed_on"], "2026-08-13"
                )

    def test_accepts_comma_or_semicolon_delimited_csv(self) -> None:
        for delimiter in (",", ";"):
            with (
                self.subTest(delimiter=delimiter),
                tempfile.TemporaryDirectory() as directory,
            ):
                template = self._template(directory)
                rows = _read_rows(template)
                _save_rows(template, rows, delimiter=delimiter)
                self._fill(template, delimiter=delimiter)
                result = import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )
                self.assertEqual(result.count, 1)

    def test_rejects_missing_unknown_and_duplicate_keys(self) -> None:
        for case in ("missing", "unknown", "duplicate"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                rows = _read_rows(template)
                if case == "missing":
                    rows.pop()
                elif case == "unknown":
                    rows[-1]["key"] = "new-product"
                else:
                    rows[-1]["key"] = rows[0]["key"]
                _save_rows(template, rows)
                self._fill(template)

                with self.assertRaises(PriceImportErrors):
                    import_prices_csv(
                        template, Path(directory), today=TODAY, now=NOW
                    )

    def test_validates_product_package_date_and_source(self) -> None:
        cases = (
            ("product_reference", "Changed product", "do not change"),
            ("observed_package", "", "provide the observed package"),
            ("observed_on", "2026-08-14", "cannot be in the future"),
            ("observed_on", "13/08/2026", "YYYY-MM-DD"),
            ("declared_source", "", "provide the declared source"),
            ("declared_source", "site\nextra product", "invalid declared source"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                self._fill(template)
                rows = _read_rows(template)
                rows[0][field] = value
                _save_rows(template, rows)

                with self.assertRaisesRegex(PriceImportErrors, message):
                    import_prices_csv(
                        template, Path(directory), today=TODAY, now=NOW
                    )

    def test_validates_store_channel_price_type_and_quantity_mode(self) -> None:
        cases = (
            ("store_location", "Walmart Toronto", "No Frills location"),
            ("store_location", "No Frills Ottawa", "No Frills location"),
            ("store_location", "No Frills Toronto", "address or postal code"),
            ("channel", "flyer", "channel must be"),
            ("price_type", "promotion", "only regular price_type"),
            ("quantity_mode", "approximate", "quantity_mode must be"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                self._fill(template)
                rows = _read_rows(template)
                rows[0][field] = value
                _save_rows(template, rows)

                with self.assertRaisesRegex(PriceImportErrors, message):
                    import_prices_csv(
                        template, Path(directory), today=TODAY, now=NOW
                    )

    def test_accepts_all_three_channels_with_fixed_packages(self) -> None:
        for channel in ("official-site", "store-label", "final-receipt"):
            with self.subTest(channel=channel), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                self._fill(template, channel=channel)
                result = import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )
                self.assertEqual(result.count, 1)

    def test_rejects_promotions_and_formula_prefixes(self) -> None:
        cases = (
            ("observed_package", "=1+1 packages", "invalid observed package"),
            ("store_location", "+No Frills 345 Toronto", "invalid store location"),
            ("declared_source", "@receipt", "invalid declared source"),
            ("declared_source", "sale 2 for CAD$5", "promotions"),
            ("declared_source", "3 for $10", "promotions"),
            ("declared_source", "buy 2 get 1", "promotions"),
            ("declared_source", "clearance shelf label", "promotions"),
            ("declared_source", "buyer@example.com", "invalid declared source"),
            ("declared_source", "call 416-555-1234", "invalid declared source"),
            (
                "declared_source",
                "card 4111 1111 1111 1111",
                "invalid declared source",
            ),
            ("declared_source", "receipt #12345", "invalid declared source"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                template = self._template(directory)
                self._fill(template)
                rows = _read_rows(template)
                rows[0][field] = value
                _save_rows(template, rows)
                with self.assertRaisesRegex(PriceImportErrors, message):
                    import_prices_csv(
                        template, Path(directory), today=TODAY, now=NOW
                    )

    def test_requires_one_exact_store_location_per_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            self._fill(template, index=0)
            self._fill(
                template,
                index=1,
                store_location="No Frills - 900 Dufferin St, Toronto, ON",
            )

            with self.assertRaisesRegex(PriceImportErrors, "same exact"):
                import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )

    def test_final_receipt_weight_requires_final_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            self._fill(
                template,
                observed_package="final weight 1.2 kg",
                channel="official-site",
                quantity_mode="final-receipt-weight",
                declared_source="official product page",
            )
            with self.assertRaisesRegex(PriceImportErrors, "final-receipt"):
                import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )

        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            self._fill(
                template,
                observed_package="final weight 1.18 kg",
                quantity_mode="final-receipt-weight",
            )
            result = import_prices_csv(
                template, Path(directory), today=TODAY, now=NOW
            )
            self.assertEqual(result.count, 1)

    def test_rejects_malformed_csv_changed_header_and_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            template.write_text("wrong,header\n", encoding="utf-8-sig")
            with self.assertRaisesRegex(PriceImportErrors, "create-template"):
                import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )

        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            with template.open("a", encoding="utf-8") as file:
                file.write('"unterminated row')
            with self.assertRaisesRegex(PriceImportErrors, "malformed"):
                import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )

        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            template.write_bytes(b"x" * 1_000_001)
            with self.assertRaisesRegex(PriceImportErrors, "1 MB limit"):
                import_prices_csv(
                    template, Path(directory), today=TODAY, now=NOW
                )

    def test_warns_when_observation_is_more_than_seven_days_old(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            self._fill(template, observed_on="2026-08-01")
            result = import_prices_csv(
                template, Path(directory), today=TODAY, now=NOW
            )

            self.assertEqual(len(result.warnings), 1)
            self.assertIn("12 days ago", result.warnings[0])

    def test_new_template_recovers_from_old_header_and_imports_latest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_directory = Path(directory)
            old = output_directory / "no-frills-toronto-prices.csv"
            old.write_text("old,header\n", encoding="utf-8-sig")
            with patch(
                "manual_prices._outputs_directory",
                return_value=output_directory,
            ):
                self.assertEqual(main(["create-template"]), 0)
                new = output_directory / "no-frills-toronto-prices-2.csv"
                self.assertTrue(new.is_file())
                self._fill(new)
                result = import_prices_csv(today=TODAY, now=NOW)

            self.assertEqual(result.count, 1)

    def test_snapshot_cannot_change_plan_catalog_or_integration(self) -> None:
        root = Path(__file__).resolve().parents[1]
        catalog_path = root / "data" / "simulated-prices.json"
        integration_path = root / "data" / "store-integrations.json"
        catalog_bytes_before = catalog_path.read_bytes()
        integration_bytes_before = integration_path.read_bytes()
        catalog_before = load_simulated_catalog()
        plan_before = generate_plan(parse_request(BASE_CASE))
        pilot_before = load_pilot_integration()

        with tempfile.TemporaryDirectory() as directory:
            template = self._template(directory)
            self._fill(template, price="9999.99")
            first = import_prices_csv(
                template, Path(directory), today=TODAY, now=NOW
            )
            second = import_prices_csv(
                template, Path(directory), today=TODAY, now=NOW
            )
            snapshot = json.loads(first.path.read_text(encoding="utf-8"))

        catalog_after = load_simulated_catalog()
        plan_after = generate_plan(parse_request(BASE_CASE))
        pilot_after = load_pilot_integration()

        self.assertNotEqual(first.path, second.path)
        self.assertEqual(snapshot["observations"][0]["price_cents"], 999999)
        for forbidden_field in (
            "real_prices_available",
            "price_source",
            "products",
            "package_price",
        ):
            self.assertNotIn(forbidden_field, snapshot)
        self.assertEqual(catalog_path.read_bytes(), catalog_bytes_before)
        self.assertEqual(integration_path.read_bytes(), integration_bytes_before)
        self.assertEqual(catalog_after, catalog_before)
        self.assertEqual(catalog_after.price_type, "simulated")
        self.assertEqual(plan_after, plan_before)
        assert plan_after is not None
        self.assertEqual(plan_after.estimated_total, 58.25)
        self.assertEqual(plan_after.budget_balance, 21.75)
        self.assertEqual(plan_after.price_type, "simulated")
        self.assertEqual(pilot_after, pilot_before)
        self.assertEqual(pilot_after.price_source, "simulated")
        self.assertEqual(pilot_after.price_status, "available")
        self.assertFalse(pilot_after.can_use_real_prices)
        self.assertFalse(pilot_after.real_prices_available)
        self.assertFalse(pilot_after.can_deliver_list)


if __name__ == "__main__":
    unittest.main()
