"""Clean household transaction records and quarantine unsafe rows."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "raw" / "diaries_transactions_all.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_REPORT = PROJECT_ROOT / "docs" / "data_quality_report.md"
REQUIRED_COLUMNS = ("hh_ids", "trx_date", "trx_value_kes", "trx_direction")
CLEAN_FILE = "transactions_cleaned.csv"
QUARANTINE_FILE = "transactions_quarantined.csv"
SUMMARY_FILE = "cleaning_summary.json"
REPORT_SECTION = "## Cleaning results"


def _normalize_column_name(column: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", column.strip().casefold())
    return normalized.strip("_")


def _count_repeated_hashes(
    hashes: Any,
    seen_hashes: set[int],
) -> list[int]:
    """Return positions whose full-row fingerprints were already encountered."""
    new_hashes: set[int] = set()
    duplicate_positions: list[int] = []
    for position, row_hash in enumerate(hashes):
        value = int(row_hash)
        if value in seen_hashes or value in new_hashes:
            duplicate_positions.append(position)
        else:
            new_hashes.add(value)
    seen_hashes.update(new_hashes)
    return duplicate_positions


def _append_cleaning_results(
    report_path: Path,
    summary: dict[str, Any],
) -> None:
    if report_path.is_file():
        existing = report_path.read_text(encoding="utf-8")
        base = existing.split(REPORT_SECTION, maxsplit=1)[0].rstrip()
    else:
        base = (
            "# Raw Data Quality Report\n\n"
            "Run `python src\\inspect_data.py` to generate the dataset profile.\n"
        )

    section = [
        REPORT_SECTION,
        "",
        f"- Source rows processed: {summary['source_rows']:,}",
        f"- Clean rows: {summary['cleaned_rows']:,}",
        f"- Quarantined rows: {summary['quarantined_rows']:,}",
        "- Rejection counts by reason (a row can have multiple reasons):",
    ]
    section.extend(
        f"  - {reason}: {count:,}"
        for reason, count in summary["reason_counts"].items()
    )
    section.extend(
        [
            "",
            "Decisions: whitespace is trimmed in clean output; recognized "
            "directions are standardized to `Inflow` / `Outflow`; transaction "
            "dates are written as ISO dates; KES amounts are numeric. Missing "
            "or unrecognized critical values and repeated exact rows are "
            "quarantined, not silently discarded. Reused `trx_id` values alone "
            "are not treated as duplicates.",
            "",
            f"Outputs: `{summary['clean_file']}`, "
            f"`{summary['quarantine_file']}`, and `{summary['summary_file']}`.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        f"{base}\n\n" + "\n".join(section),
        encoding="utf-8",
    )


def clean_dataset(
    source_path: Path = DEFAULT_SOURCE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = DEFAULT_REPORT,
    chunksize: int = 50_000,
) -> dict[str, Any]:
    """Write cleaned and quarantined CSVs without changing the source."""
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    report_path = Path(report_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Source CSV was not found: {source_path}")
    if source_path.stat().st_size == 0:
        raise ValueError(f"Source CSV is empty: {source_path}")
    if chunksize < 1:
        raise ValueError("chunksize must be greater than zero")

    try:
        original_columns = pd.read_csv(source_path, nrows=0).columns.tolist()
    except pd.errors.EmptyDataError as error:
        raise ValueError(f"Source CSV has no header: {source_path}") from error

    normalized_columns = [
        _normalize_column_name(column) for column in original_columns
    ]
    if any(not column for column in normalized_columns):
        raise ValueError("Source CSV contains a column name that normalizes to empty")
    if len(set(normalized_columns)) != len(normalized_columns):
        raise ValueError("Column names are not unique after normalization")
    missing_columns = set(REQUIRED_COLUMNS).difference(normalized_columns)
    if missing_columns:
        raise ValueError(
            "Source CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )
    if "source_row_number" in normalized_columns:
        raise ValueError(
            "Source CSV already contains reserved column 'source_row_number'"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    clean_path = output_dir / CLEAN_FILE
    quarantine_path = output_dir / QUARANTINE_FILE
    clean_temp_path = output_dir / f".{CLEAN_FILE}.tmp"
    quarantine_temp_path = output_dir / f".{QUARANTINE_FILE}.tmp"
    summary_path = output_dir / SUMMARY_FILE

    seen_row_hashes: set[int] = set()
    source_rows = 0
    cleaned_rows = 0
    quarantined_rows = 0
    reason_counts = {
        "missing_household_id": 0,
        "invalid_transaction_date": 0,
        "missing_or_non_numeric_amount": 0,
        "missing_or_unrecognized_direction": 0,
        "exact_duplicate_record": 0,
    }
    clean_written = False
    quarantine_written = False

    for raw_chunk in pd.read_csv(
        source_path,
        chunksize=chunksize,
        low_memory=False,
        dtype="string",
    ):
        source_rows += len(raw_chunk)
        raw_chunk.columns = normalized_columns

        row_hashes = pd.util.hash_pandas_object(raw_chunk, index=False).to_numpy(
            dtype="uint64"
        )
        duplicate_positions = _count_repeated_hashes(
            row_hashes,
            seen_row_hashes,
        )
        exact_duplicate = pd.Series(False, index=raw_chunk.index, dtype=bool)
        if duplicate_positions:
            exact_duplicate.iloc[duplicate_positions] = True

        cleaned = raw_chunk.apply(lambda column: column.str.strip())
        household_id = cleaned["hh_ids"]
        transaction_date = pd.to_datetime(
            cleaned["trx_date"],
            format="%d%b%Y",
            errors="coerce",
        )
        amount = pd.to_numeric(cleaned["trx_value_kes"], errors="coerce")
        direction_key = cleaned["trx_direction"].str.casefold()
        standardized_direction = direction_key.map(
            {"inflow": "Inflow", "outflow": "Outflow"}
        )

        rejection_reasons = pd.Series(
            "",
            index=cleaned.index,
            dtype="string",
        )
        rejection_checks = (
            (
                "missing_household_id",
                household_id.isna() | household_id.eq(""),
            ),
            ("invalid_transaction_date", transaction_date.isna()),
            ("missing_or_non_numeric_amount", amount.isna()),
            (
                "missing_or_unrecognized_direction",
                standardized_direction.isna(),
            ),
            ("exact_duplicate_record", exact_duplicate),
        )
        for reason, invalid_rows in rejection_checks:
            reason_value = rejection_reasons.where(
                rejection_reasons.eq(""),
                rejection_reasons + ";",
            ) + reason
            rejection_reasons = rejection_reasons.mask(invalid_rows, reason_value)
            reason_counts[reason] += int(invalid_rows.sum())

        rejected_mask = rejection_reasons.ne("")
        source_row_numbers = range(source_rows - len(raw_chunk) + 1, source_rows + 1)

        clean_output = cleaned.loc[~rejected_mask].copy()
        clean_output["trx_date"] = transaction_date.loc[~rejected_mask].dt.strftime(
            "%Y-%m-%d"
        )
        clean_output["trx_value_kes"] = amount.loc[~rejected_mask]
        clean_output["trx_direction"] = standardized_direction.loc[~rejected_mask]
        row_numbers = list(source_row_numbers)
        clean_output.insert(0, "source_row_number", [
            row_number
            for row_number, is_rejected in zip(row_numbers, rejected_mask)
            if not is_rejected
        ])

        quarantine_output = raw_chunk.loc[rejected_mask].copy()
        quarantine_output.insert(
            0,
            "source_row_number",
            [
                row_number
                for row_number, is_rejected in zip(row_numbers, rejected_mask)
                if is_rejected
            ],
        )
        quarantine_output["rejection_reason"] = rejection_reasons.loc[
            rejected_mask
        ].tolist()

        if not clean_output.empty:
            clean_output.to_csv(
                clean_temp_path,
                mode="a" if clean_written else "w",
                header=not clean_written,
                index=False,
            )
            clean_written = True
        if not quarantine_output.empty:
            quarantine_output.to_csv(
                quarantine_temp_path,
                mode="a" if quarantine_written else "w",
                header=not quarantine_written,
                index=False,
            )
            quarantine_written = True

        cleaned_rows += len(clean_output)
        quarantined_rows += len(quarantine_output)

    output_columns = ["source_row_number", *normalized_columns]
    if not clean_written:
        pd.DataFrame(columns=output_columns).to_csv(clean_temp_path, index=False)
    if not quarantine_written:
        pd.DataFrame(
            columns=[*output_columns, "rejection_reason"]
        ).to_csv(quarantine_temp_path, index=False)

    clean_temp_path.replace(clean_path)
    quarantine_temp_path.replace(quarantine_path)

    summary: dict[str, Any] = {
        "source_file": source_path.name,
        "source_rows": source_rows,
        "cleaned_rows": cleaned_rows,
        "quarantined_rows": quarantined_rows,
        "reason_counts": reason_counts,
        "clean_file": clean_path.name,
        "quarantine_file": quarantine_path.name,
        "summary_file": summary_path.name,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _append_cleaning_results(report_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--chunksize", type=int, default=50_000)
    args = parser.parse_args()

    summary = clean_dataset(
        args.source,
        args.output_dir,
        args.report,
        args.chunksize,
    )
    print(
        f"Cleaning complete: {summary['source_rows']:,} source rows, "
        f"{summary['cleaned_rows']:,} clean, "
        f"{summary['quarantined_rows']:,} quarantined."
    )
    print(f"Quality report updated: {args.report}")
    print(f"Summary: {args.output_dir / SUMMARY_FILE}")


if __name__ == "__main__":
    main()
