"""Full-refresh the PostgreSQL transactions table from the cleaned CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

if __package__:
    from .config import (
        PROJECT_ROOT,
        create_database_engine,
        get_database_settings,
        test_database_connection,
    )
else:
    from config import (
        PROJECT_ROOT,
        create_database_engine,
        get_database_settings,
        test_database_connection,
    )

DEFAULT_CSV = PROJECT_ROOT / "data" / "processed" / "transactions_cleaned.csv"
CREATE_TABLE_SQL = PROJECT_ROOT / "sql" / "01_create_tables.sql"
HOUSEHOLD_METRICS_SQL = PROJECT_ROOT / "sql" / "02_household_metrics.sql"
TABLE_NAME = "transactions"
SCHEMA_NAME = "public"
CSV_CHUNK_SIZE = 10_000
INSERT_CHUNK_SIZE = 500

TEXT_COLUMNS = (
    "hh_ids",
    "first_trx_date_hh",
    "last_trx_date_hh",
    "interview_designation",
    "int_date",
    "int_yr_mo",
    "first_int_date",
    "account_ids",
    "m_ids_owner",
    "account_bsheet_desig",
    "account_startclose_balance",
    "account_formal",
    "account_liquid",
    "first_trx_date_acc",
    "last_trx_date_acc",
    "trx_id",
    "m_ids_trx",
    "trx_yr_mo",
    "trx_class_code",
    "trx_class_desc",
    "trx_family_code",
    "trx_family_desc",
    "trx_type_desc",
    "trx_prx_purpose",
    "trx_prx_purpose_fd",
    "trx_bsheet_direction",
    "trx_mode_desc",
    "trx_outlet",
    "trx_direction",
    "trx_inkind_units",
)
INTEGER_COLUMNS = (
    "source_row_number",
    "unique_hhs",
    "tot_hh_daysofobs",
    "tot_hh_monthsofobs",
    "int_month",
    "int_year",
    "unique_accnts",
    "unique_hm_owner",
    "tot_acc_daysofobs",
    "tot_acc_monthsofobs",
    "trx_month",
    "trx_year",
    "trx_dq_round",
    "trx_stdtime_days_hh",
    "trx_stdtime_mnths_hh",
    "trx_stdtime_days_acc",
    "trx_stdtime_mnths_acc",
    "trx_type_code",
    "trx_mode_code",
    "trx_place_incommunity",
    "ddd_gift",
)
DECIMAL_COLUMNS = (
    "trx_fee",
    "trx_distance_km",
    "trx_value_kes",
    "trx_value_usd",
    "trx_inkind_value_usd",
    "trx_inkind_value_kes",
    "trx_stdtime_mnths_hh_nr",
)


def _prepare_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Convert CSV fields to types that match the inspected PostgreSQL schema."""
    for column in INTEGER_COLUMNS:
        chunk[column] = pd.to_numeric(chunk[column], errors="raise").astype("Int64")
    for column in DECIMAL_COLUMNS:
        chunk[column] = pd.to_numeric(chunk[column], errors="raise").astype("Float64")
    chunk["trx_date"] = pd.to_datetime(
        chunk["trx_date"],
        format="%Y-%m-%d",
        errors="raise",
    )
    return chunk


def _validate_table_columns(connection: Connection, csv_columns: list[str]) -> None:
    database_columns = {
        column["name"]
        for column in inspect(connection).get_columns(TABLE_NAME, schema=SCHEMA_NAME)
    }
    csv_column_set = set(csv_columns)
    if csv_column_set != database_columns:
        missing_in_csv = sorted(database_columns - csv_column_set)
        missing_in_table = sorted(csv_column_set - database_columns)
        raise RuntimeError(
            "The existing public.transactions schema does not match the cleaned "
            f"CSV. Missing in CSV: {missing_in_csv}; missing in table: "
            f"{missing_in_table}. No table rows were changed."
        )


def _execute_sql_file(connection: Connection, path: Path) -> None:
    statement = path.read_text(encoding="utf-8").strip()
    if not statement:
        raise ValueError(f"SQL file is empty: {path}")
    connection.exec_driver_sql(statement)


def load_cleaned_csv(
    csv_path: Path = DEFAULT_CSV,
    csv_chunksize: int = CSV_CHUNK_SIZE,
    insert_chunksize: int = INSERT_CHUNK_SIZE,
) -> dict[str, Any]:
    """Create the table, full-refresh it transactionally, and create its metrics view."""
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Cleaned CSV was not found: {csv_path}")
    if csv_path.stat().st_size == 0:
        raise ValueError(f"Cleaned CSV is empty: {csv_path}")
    if csv_chunksize < 1 or insert_chunksize < 1:
        raise ValueError("Both chunk sizes must be greater than zero")

    csv_columns = pd.read_csv(csv_path, nrows=0).columns.tolist()
    required_columns = {"source_row_number", "hh_ids", "trx_date", "trx_direction", "trx_value_kes"}
    missing_columns = required_columns.difference(csv_columns)
    if missing_columns:
        raise ValueError(
            "Cleaned CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    settings = get_database_settings()
    engine = create_database_engine(settings)
    loaded_rows = 0
    try:
        with engine.begin() as connection:
            _execute_sql_file(connection, CREATE_TABLE_SQL)
            _validate_table_columns(connection, csv_columns)
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_transactions_household_date "
                "ON public.transactions (hh_ids, trx_date)"
            )
            connection.exec_driver_sql("TRUNCATE TABLE public.transactions")

            chunks = pd.read_csv(
                csv_path,
                chunksize=csv_chunksize,
                dtype={column: "string" for column in TEXT_COLUMNS},
                low_memory=False,
            )
            for chunk in chunks:
                prepared = _prepare_chunk(chunk)
                prepared.to_sql(
                    TABLE_NAME,
                    con=connection,
                    schema=SCHEMA_NAME,
                    if_exists="append",
                    index=False,
                    chunksize=insert_chunksize,
                    method="multi",
                )
                loaded_rows += len(prepared)

            database_rows = int(
                connection.execute(
                    text("SELECT COUNT(*) FROM public.transactions")
                ).scalar_one()
            )
            if database_rows != loaded_rows:
                raise RuntimeError(
                    "Loaded row-count verification failed: "
                    f"CSV={loaded_rows:,}, database={database_rows:,}. "
                    "The transaction will be rolled back."
                )

            _execute_sql_file(connection, HOUSEHOLD_METRICS_SQL)
            sample_rows = connection.execute(
                text(
                    "SELECT household_id, month_start, total_inflows_kes, "
                    "total_outflows_kes, net_cash_flow_kes, earned_income_kes "
                    "FROM public.vw_household_monthly_metrics "
                    "ORDER BY month_start, household_id LIMIT 5"
                )
            ).all()
    except SQLAlchemyError:
        raise RuntimeError(
            "PostgreSQL operation failed for "
            f"{settings.database} at {settings.host}:{settings.port}. "
            "The load transaction was rolled back; credentials were not displayed."
        ) from None
    finally:
        engine.dispose()

    result = {
        "csv_rows": loaded_rows,
        "database_rows": database_rows,
        "sample_metrics": sample_rows,
        "database": settings.database,
    }
    print(
        f"Full refresh complete: loaded {loaded_rows:,} rows into "
        f"{settings.database}. Database count verified."
    )
    print("Sample household-month metrics:")
    for row in sample_rows:
        print(f"  {row}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--csv-chunksize", type=int, default=CSV_CHUNK_SIZE)
    parser.add_argument("--insert-chunksize", type=int, default=INSERT_CHUNK_SIZE)
    args = parser.parse_args()

    test_database_connection()
    load_cleaned_csv(
        args.csv,
        csv_chunksize=args.csv_chunksize,
        insert_chunksize=args.insert_chunksize,
    )


if __name__ == "__main__":
    main()
