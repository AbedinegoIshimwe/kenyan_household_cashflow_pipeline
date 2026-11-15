import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.clean_data import clean_dataset


class CleanDatasetTests(unittest.TestCase):
    def test_cleans_valid_rows_and_quarantines_unsafe_records(self):
        source = pd.DataFrame(
            {
                "hh_ids": ["HH01", "HH01", "HH01", "HH02", "HH03"],
                "trx_id": ["T01", "T01", "T01", "T02", "T03"],
                "m_ids_owner": ["M01", "M01", "M01", "M02", "M03"],
                "account_ids": ["A01", "A01", "A01", "A02", "A03"],
                "trx_date": [
                    "03sep2012",
                    "03sep2012",
                    "04sep2012",
                    "05sep2012",
                    "06sep2012",
                ],
                "trx_value_kes": ["100", "100", "40", "20", None],
                "trx_direction": [
                    " inflow ",
                    " inflow ",
                    "OUTFLOW",
                    None,
                    "Inflow",
                ],
                "trx_family_desc": [
                    "Income ",
                    "Income ",
                    "Borrowing",
                    "Expense",
                    "Food",
                ],
                "trx_type_desc": [
                    "Wages",
                    "Wages",
                    "Loan repayment",
                    "Food",
                    "Groceries",
                ],
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "raw.csv"
            output_dir = root / "processed"
            report_path = root / "docs" / "data_quality_report.md"
            source.to_csv(source_path, index=False)
            original_bytes = source_path.read_bytes()
            report_path.parent.mkdir(parents=True)
            report_path.write_text("# Profile\n\nExisting profile content.\n")

            summary = clean_dataset(
                source_path,
                output_dir,
                report_path,
                chunksize=2,
            )

            cleaned = pd.read_csv(
                output_dir / "transactions_cleaned.csv",
                dtype={"hh_ids": "string", "trx_id": "string"},
            )
            quarantined = pd.read_csv(
                output_dir / "transactions_quarantined.csv",
                dtype="string",
            )

            self.assertEqual(source_path.read_bytes(), original_bytes)
            self.assertEqual(summary["source_rows"], 5)
            self.assertEqual(summary["cleaned_rows"], 2)
            self.assertEqual(summary["quarantined_rows"], 3)
            self.assertEqual(summary["reason_counts"]["exact_duplicate_record"], 1)
            self.assertEqual(
                summary["reason_counts"]["missing_or_unrecognized_direction"],
                1,
            )
            self.assertEqual(
                summary["reason_counts"]["missing_or_non_numeric_amount"],
                1,
            )
            self.assertEqual(cleaned["source_row_number"].tolist(), [1, 3])
            self.assertEqual(cleaned.loc[0, "trx_date"], "2012-09-03")
            self.assertEqual(cleaned.loc[0, "trx_direction"], "Inflow")
            self.assertEqual(cleaned.loc[1, "trx_direction"], "Outflow")
            self.assertEqual(cleaned.loc[1, "trx_family_desc"], "Borrowing")
            self.assertEqual(cleaned.loc[0, "m_ids_owner"], "M01")
            self.assertIn("exact_duplicate_record", quarantined["rejection_reason"].tolist())
            self.assertIn("## Cleaning results", report_path.read_text())
            persisted_summary = json.loads(
                (output_dir / "cleaning_summary.json").read_text()
            )
            self.assertEqual(persisted_summary["cleaned_rows"], 2)


if __name__ == "__main__":
    unittest.main()
