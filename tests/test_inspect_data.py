import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.inspect_data import inspect_dataset, render_report


class InspectDatasetTests(unittest.TestCase):
    def test_profiles_rows_nulls_duplicates_dates_and_categories(self):
        source = pd.DataFrame(
            {
                "hh_ids": ["HH01", "HH01", "HH02"],
                "trx_id": ["T01", "T01", "T02"],
                "trx_date": ["03sep2012", "03sep2012", "04sep2012"],
                "trx_direction": ["Inflow", "Inflow", None],
                "trx_value_kes": ["100", "100", None],
                "trx_family_desc": ["Income", "Income", "Food"],
                "trx_type_desc": ["Wages", "Wages", "Groceries"],
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "raw.csv"
            source.to_csv(source_path, index=False)

            report = inspect_dataset(source_path, chunksize=2)
            markdown = render_report(report)

        self.assertEqual(report["row_count"], 3)
        self.assertEqual(report["column_count"], 7)
        self.assertEqual(report["unique_households"], 2)
        self.assertEqual(report["unique_categories"]["trx_family_desc"], 2)
        self.assertEqual(report["exact_duplicate_row_fingerprint_candidates"], 1)
        self.assertEqual(
            report["duplicate_transaction_ids"]["rows_after_first_occurrence"],
            1,
        )
        self.assertEqual(report["date_range"]["min"], "2012-09-03")
        self.assertEqual(report["date_range"]["max"], "2012-09-04")
        self.assertEqual(
            report["null_counts"]["trx_value_kes"]["percent"],
            33.33,
        )
        self.assertIn("Key data-quality risks", markdown)
        self.assertIn("Household metric classification limits", markdown)
        self.assertIn("Cleaning decisions", markdown)


if __name__ == "__main__":
    unittest.main()
