"""Profile the raw Kenya Financial Diaries transaction CSV."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "raw" / "diaries_transactions_all.csv"
DEFAULT_REPORT = PROJECT_ROOT / "docs" / "data_quality_report.md"
CLEANING_SUMMARY = PROJECT_ROOT / "data" / "processed" / "cleaning_summary.json"

FREE_TEXT_COLUMNS = (
    "trx_family_desc",
    "trx_type_desc",
    "trx_prx_purpose",
    "trx_prx_purpose_fd",
    "trx_mode_desc",
    "trx_place_incommunity",
    "trx_outlet",
)
CATEGORY_COLUMNS = ("trx_family_desc", "trx_type_desc")
TEXT_SAMPLE_LIMIT = 10


def _count_repeated_hashes(
    hashes: Any,
    seen_hashes: set[int],
) -> int:
    repeated = 0
    new_hashes: set[int] = set()
    for row_hash in hashes:
        value = int(row_hash)
        if value in seen_hashes or value in new_hashes:
            repeated += 1
        else:
            new_hashes.add(value)
    seen_hashes.update(new_hashes)
    return repeated


def inspect_dataset(source_path: Path, chunksize: int = 50_000) -> dict[str, Any]:
    """Scan the CSV in chunks and return a reproducible profile."""
    source_path = Path(source_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Source CSV was not found: {source_path}")
    if source_path.stat().st_size == 0:
        raise ValueError(f"Source CSV is empty: {source_path}")
    if chunksize < 1:
        raise ValueError("chunksize must be greater than zero")

    try:
        columns = pd.read_csv(source_path, nrows=0).columns.tolist()
    except pd.errors.EmptyDataError as error:
        raise ValueError(f"Source CSV has no header: {source_path}") from error

    sample = pd.read_csv(source_path, nrows=1000, low_memory=False)
    missing_columns = [
        column
        for column in (
            "hh_ids",
            "trx_id",
            "trx_date",
            "trx_direction",
            "trx_value_kes",
            *CATEGORY_COLUMNS,
        )
        if column not in columns
    ]

    null_counts = {column: 0 for column in columns}
    text_samples: dict[str, list[str]] = {
        column: [] for column in FREE_TEXT_COLUMNS if column in columns
    }
    text_sample_sets: dict[str, set[str]] = {
        column: set() for column in text_samples
    }
    unique_text_values: dict[str, set[str]] = {
        column: set() for column in text_samples
    }
    text_whitespace_rows = {column: 0 for column in text_samples}
    households: set[str] = set()
    transaction_ids_seen: set[str] = set()
    repeated_transaction_ids: set[str] = set()
    category_values: dict[str, set[str]] = {
        column: set() for column in CATEGORY_COLUMNS if column in columns
    }
    direction_counts: dict[str, int] = {}
    seen_row_hashes: set[int] = set()
    exact_duplicate_rows = 0
    repeated_transaction_id_rows = 0
    invalid_date_rows = 0
    invalid_amount_rows = 0
    amount_values: list[float] = []
    date_min: pd.Timestamp | None = None
    date_max: pd.Timestamp | None = None
    row_count = 0

    for chunk in pd.read_csv(
        source_path,
        chunksize=chunksize,
        low_memory=False,
        dtype="string",
    ):
        row_count += len(chunk)
        for column in columns:
            null_counts[column] += int(chunk[column].isna().sum())

        hashes = pd.util.hash_pandas_object(
            chunk.astype("string"),
            index=False,
        ).to_numpy(dtype="uint64")
        exact_duplicate_rows += _count_repeated_hashes(hashes, seen_row_hashes)

        if "hh_ids" in chunk:
            household_values = chunk["hh_ids"].dropna().str.strip()
            households.update(
                value for value in household_values.tolist() if value
            )
        if "trx_id" in chunk:
            for transaction_id in chunk["trx_id"].dropna().str.strip():
                if not transaction_id:
                    continue
                if transaction_id in transaction_ids_seen:
                    repeated_transaction_id_rows += 1
                    repeated_transaction_ids.add(transaction_id)
                else:
                    transaction_ids_seen.add(transaction_id)

        if "trx_date" in chunk:
            parsed_dates = pd.to_datetime(
                chunk["trx_date"].str.strip(),
                format="%d%b%Y",
                errors="coerce",
            )
            invalid_date_rows += int(
                (chunk["trx_date"].notna() & parsed_dates.isna()).sum()
            )
            valid_dates = parsed_dates.dropna()
            if not valid_dates.empty:
                chunk_min = valid_dates.min()
                chunk_max = valid_dates.max()
                date_min = chunk_min if date_min is None else min(date_min, chunk_min)
                date_max = chunk_max if date_max is None else max(date_max, chunk_max)

        if "trx_value_kes" in chunk:
            numeric_amounts = pd.to_numeric(
                chunk["trx_value_kes"],
                errors="coerce",
            )
            invalid_amount_rows += int(
                (chunk["trx_value_kes"].notna() & numeric_amounts.isna()).sum()
            )
            amount_values.extend(numeric_amounts.dropna().astype(float).tolist())

        if "trx_direction" in chunk:
            normalized_directions = (
                chunk["trx_direction"].str.strip().str.casefold()
            )
            for direction, count in normalized_directions.value_counts(
                dropna=False
            ).items():
                if pd.isna(direction) or not direction:
                    label = "Missing"
                elif direction == "inflow":
                    label = "Inflow"
                elif direction == "outflow":
                    label = "Outflow"
                else:
                    label = f"Other: {direction}"
                direction_counts[label] = direction_counts.get(label, 0) + int(count)

        for column, values in category_values.items():
            non_null_values = chunk[column].dropna()
            values.update(value for value in non_null_values.tolist() if value)

        for column in text_samples:
            non_null_values = chunk[column].dropna().astype("string")
            text_whitespace_rows[column] += int(
                non_null_values.ne(non_null_values.str.strip()).sum()
            )
            non_null_values = non_null_values.drop_duplicates()
            for value in non_null_values:
                if not value:
                    continue
                unique_text_values[column].add(value)
                if len(text_samples[column]) < TEXT_SAMPLE_LIMIT:
                    if value not in text_sample_sets[column]:
                        text_samples[column].append(value)
                        text_sample_sets[column].add(value)

    if amount_values:
        amount_stats = pd.Series(amount_values, dtype="float64").describe(
            percentiles=[0.25, 0.5, 0.75]
        )

        def finite_number(value: Any) -> float | None:
            number = float(value)
            return number if math.isfinite(number) else None

        amount_summary: dict[str, float | int | None] = {
            "valid_count": int(amount_stats["count"]),
            "sum_kes": finite_number(
                pd.Series(amount_values, dtype="float64").sum()
            ),
            "mean_kes": finite_number(amount_stats["mean"]),
            "std_kes": finite_number(amount_stats["std"]),
            "min_kes": finite_number(amount_stats["min"]),
            "25_percentile_kes": finite_number(amount_stats["25%"]),
            "median_kes": finite_number(amount_stats["50%"]),
            "75_percentile_kes": finite_number(amount_stats["75%"]),
            "max_kes": finite_number(amount_stats["max"]),
        }
    else:
        amount_summary = {"valid_count": 0}

    return {
        "source_file": source_path.name,
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
        "sample_inferred_dtypes": {
            column: str(dtype) for column, dtype in sample.dtypes.items()
        },
        "dtype_sample_rows": len(sample),
        "null_counts": {
            column: {
                "count": null_counts[column],
                "percent": round(null_counts[column] / row_count * 100, 2)
                if row_count
                else 0.0,
            }
            for column in columns
        },
        "missing_expected_columns": missing_columns,
        "exact_duplicate_row_fingerprint_candidates": exact_duplicate_rows,
        "duplicate_transaction_ids": {
            "rows_after_first_occurrence": repeated_transaction_id_rows,
            "distinct_ids_reused": len(repeated_transaction_ids),
            "examples": sorted(repeated_transaction_ids)[:10],
        },
        "date_range": {
            "min": date_min.strftime("%Y-%m-%d") if date_min is not None else None,
            "max": date_max.strftime("%Y-%m-%d") if date_max is not None else None,
            "invalid_non_null_dates": invalid_date_rows,
        },
        "direction_counts": direction_counts,
        "unique_households": len(households),
        "unique_categories": {
            column: len(values) for column, values in category_values.items()
        },
        "trx_value_kes_numeric_conversion_failures": invalid_amount_rows,
        "trx_value_kes_summary": amount_summary,
        "free_text_samples": {
            column: {
                "unique_value_count": len(unique_text_values[column]),
                "values_with_leading_or_trailing_whitespace": (
                    text_whitespace_rows[column]
                ),
                "samples": text_samples[column],
            }
            for column in text_samples
        },
    }


def _format_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_report(
    report: dict[str, Any],
    cleaning_summary: dict[str, Any] | None = None,
) -> str:
    """Render the profile and, when available, cleaning results as Markdown."""
    column_rows = [
        (
            column,
            report["sample_inferred_dtypes"].get(column, "not inferred"),
            f"{report['null_counts'][column]['count']:,}",
            f"{report['null_counts'][column]['percent']:.2f}%",
        )
        for column in report["columns"]
    ]
    sections = [
        "# Raw Data Quality Report",
        "",
        f"- **Source file:** `{report['source_file']}`",
        f"- **Rows:** {report['row_count']:,}",
        f"- **Columns:** {report['column_count']}",
        f"- **Data types:** inferred from the first {report['dtype_sample_rows']:,} rows.",
        "",
        "## Source columns, inferred types, and missing values",
        "",
        _format_table(
            ("Column", "Sample dtype", "Null count", "Null percent"),
            column_rows,
        ),
        "",
        "## Duplicate review",
        "",
        f"- Exact row fingerprint duplicate candidates: "
        f"{report['exact_duplicate_row_fingerprint_candidates']:,}.",
        "- Repeated transaction IDs: "
        f"{report['duplicate_transaction_ids']['rows_after_first_occurrence']:,} "
        "rows after each ID's first occurrence, across "
        f"{report['duplicate_transaction_ids']['distinct_ids_reused']:,} IDs. "
        "Repeated IDs are not assumed to be duplicate transactions.",
        "- Fingerprint matches are candidates and must be reviewed before removal.",
        "",
        "## Schema notes",
        "",
    ]
    if report["missing_expected_columns"]:
        sections.extend(
            [
                "- Expected fields missing from the source: "
                + ", ".join(f"`{column}`" for column in report["missing_expected_columns"]),
                "",
            ]
        )
    else:
        sections.extend(
            [
                "- All expected profiling fields are present. The prompt's "
                "`trx_family_de` label corresponds to the actual CSV column "
                "`trx_family_desc`.",
                "",
            ]
        )
    sections.extend(
        [
            "## Key data-quality risks",
            "",
            f"- Missing transaction direction: "
            f"{report['null_counts'].get('trx_direction', {}).get('count', 0):,} "
            "rows. These cannot safely be classified as inflow or outflow.",
            f"- Missing KES amount: "
            f"{report['null_counts'].get('trx_value_kes', {}).get('count', 0):,} "
            "rows. These cannot be used in amount-based indicators.",
            f"- Duplicate/key ambiguity: "
            f"{report['exact_duplicate_row_fingerprint_candidates']:,} exact-row "
            "fingerprint candidates and "
            f"{report['duplicate_transaction_ids']['rows_after_first_occurrence']:,} "
            "rows after first occurrence of a reused transaction ID. Repeated IDs "
            "alone are not proof of duplicate transactions.",
            "",
            "## Date range",
            "",
            f"- Earliest parsed transaction: {report['date_range']['min']}",
            f"- Latest parsed transaction: {report['date_range']['max']}",
            f"- Invalid non-null date values: "
            f"{report['date_range']['invalid_non_null_dates']:,}",
            "",
            "## Direction counts",
            "",
        ]
    )
    sections.extend(
        f"- {direction}: {count:,}"
        for direction, count in sorted(report["direction_counts"].items())
    )
    sections.extend(
        [
            "",
            "## Household and category counts",
            "",
            f"- Unique households: {report['unique_households']:,}",
        ]
    )
    sections.extend(
        f"- Unique `{column}` values: {count:,}"
        for column, count in report["unique_categories"].items()
    )
    sections.extend(
        [
            "",
            "## KES amount summary",
            "",
            f"- Non-null values that could not be converted to numeric: "
            f"{report['trx_value_kes_numeric_conversion_failures']:,}",
            _format_table(
                ("Statistic", "KES / count"),
                [
                    (
                        key.replace("_", " "),
                        f"{value:,.2f}" if value is not None else "not available",
                    )
                    for key, value in report["trx_value_kes_summary"].items()
                ],
            ),
            "",
            "## Free-text and classification samples",
            "",
            "Samples are raw values; review inconsistent spelling, casing, and "
            "overlapping meanings before creating mappings.",
            "",
            "Observed examples include mixed casing (`CLOSING BALANCE` versus "
            "`Cash`) and inconsistent punctuation (`Cash lost , stolen, missing`). "
            "These classification fields should be mapped only after reviewing "
            "the source definitions.",
            "",
        ]
    )
    for column, details in report["free_text_samples"].items():
        samples = "; ".join(f"`{value}`" for value in details["samples"])
        sections.extend(
            [
                f"### `{column}`",
                "",
                f"- Unique values: {details['unique_value_count']:,}",
                "- Rows with leading/trailing whitespace: "
                f"{details['values_with_leading_or_trailing_whitespace']:,}",
                f"- Sample values: {samples}",
                "",
            ]
        )
    sections.extend(
        [
            "## Cleaning decisions",
            "",
            "- Preserve the original raw CSV unchanged.",
            "- Standardize column names and trim surrounding whitespace.",
            "- Parse transaction dates and KES amounts without inventing missing values.",
            "- Standardize only recognized `Inflow` / `Outflow` values.",
            "- Quarantine rows missing a household, parseable date, numeric amount, "
            "or recognized direction.",
            "- Quarantine exact duplicate records after the first occurrence; "
            "do not deduplicate on `trx_id` alone.",
            "- Preserve household, member, account, transaction, and classification "
            "identifiers in outputs.",
            "",
            "## Cleaning results",
            "",
        ]
    )
    if cleaning_summary is None:
        sections.append(
            "Cleaning has not been run yet. Run `python src\\clean_data.py` "
            "to populate this section."
        )
    else:
        sections.extend(
            [
                f"- Source rows: {cleaning_summary['source_rows']:,}",
                f"- Clean rows: {cleaning_summary['cleaned_rows']:,}",
                f"- Quarantined rows: {cleaning_summary['quarantined_rows']:,}",
                "- Rows affected by each reason (reasons can overlap):",
            ]
        )
        sections.extend(
            f"  - {reason}: {count:,}"
            for reason, count in cleaning_summary["reason_counts"].items()
        )
        sections.extend(
            [
                "",
                f"Outputs: `{cleaning_summary['clean_file']}`, "
                f"`{cleaning_summary['quarantine_file']}`, and "
                f"`{cleaning_summary['summary_file']}`.",
            ]
        )
    sections.extend(
        [
            "",
            "## Household metric classification limits",
            "",
            "The PostgreSQL household-month view uses `hh_ids` and `trx_date`. "
            "Earned income is limited to exact, reviewed family/type pairs for "
            "regular employment, casual/temporary employment, self-employment, "
            "agriculture, and rental income.",
            "",
            "Borrowing, gifts, transfers, savings withdrawals, asset sales, "
            "resources received, non-employment, passthrough income, and "
            "ambiguous or unknown categories are not counted as earned income. "
            "Savings deposits/withdrawals and borrowing/repayments are counted "
            "only when explicitly tagged in `trx_prx_purpose_fd`; untagged "
            "transactions are not inferred. This field is missing for "
            f"{report['null_counts'].get('trx_prx_purpose_fd', {}).get('percent', 0):.2f}% "
            "of raw rows, so these indicators are partial.",
            "",
            "## Scope and limitations",
            "",
            "This historical household dataset supports descriptive financial "
            "profiling only. It does not provide verified loan performance "
            "outcomes, and household records must not be interpreted as a "
            "specific individual's complete finances. The project does not "
            "produce a validated credit score or default prediction.",
            "",
        ]
    )
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--chunksize", type=int, default=50_000)
    args = parser.parse_args()

    profile = inspect_dataset(args.source, args.chunksize)
    cleaning_summary = None
    if CLEANING_SUMMARY.is_file():
        cleaning_summary = json.loads(CLEANING_SUMMARY.read_text(encoding="utf-8"))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render_report(profile, cleaning_summary),
        encoding="utf-8",
    )

    print(f"Dataset shape: ({profile['row_count']:,}, {profile['column_count']})")
    print("\nSample-inferred data types:")
    for column, dtype in profile["sample_inferred_dtypes"].items():
        print(f"  {column}: {dtype}")
    print("Columns:")
    for column in profile["columns"]:
        print(f"  {column}")
    print("\nNull counts and percentages:")
    for column, details in profile["null_counts"].items():
        print(
            f"  {column}: {details['count']:,} "
            f"({details['percent']:.2f}%)"
        )
    print(
        "\nExact duplicate row fingerprint candidates: "
        f"{profile['exact_duplicate_row_fingerprint_candidates']:,}"
    )
    print(
        "Rows after first occurrence of a transaction ID: "
        f"{profile['duplicate_transaction_ids']['rows_after_first_occurrence']:,}"
    )
    print(f"\nData quality report: {args.report}")


if __name__ == "__main__":
    main()
