
# Alternative-Data Financial Assessment Pipeline

This project profiles and cleans Kenya Financial Diaries transactions, then
loads them into the existing PostgreSQL database `kenya_cashflow_db` for
household-month cash-flow analysis. It is descriptive analysis, not a validated
credit score or loan-default prediction model. Household records are not a
specific individual's complete finances.

The raw file is `data/raw/diaries_transactions_all.csv`; the cleaned loader
input is `data/processed/transactions_cleaned.csv`. The actual source names are
`trx_family_desc` and `account_ids` (not the brief's `trx_family_de` and
`account_id`).

## Project structure

```text
kenyan_household_cashflow_pipeline/
├── data/
│   ├── raw/                         # Original CSV; ignored by Git
│   └── processed/                   # Generated CSV/JSON; ignored by Git
├── docs/
│   └── data_quality_report.md       # Generated profiling and quality notes
├── sql/
│   ├── 01_create_tables.sql         # public.transactions table
│   └── 02_household_metrics.sql     # Household-month metrics view
├── src/
│   ├── inspect_data.py              # Profile raw data
│   ├── clean_data.py                # Clean and quarantine unsafe records
│   ├── config.py                    # Load .env and test PostgreSQL
│   └── load_data.py                 # Transactional full-refresh loader
├── tests/
│   ├── test_inspect_data.py
│   ├── test_clean_data.py
│   └── test_postgres_pipeline.py
├── .env                             # Local credentials; ignored by Git
├── .env.example                     # Safe placeholder template
├── .gitignore
├── README.md
└── requirements.txt
```

## Setup and run (PowerShell)

Run commands from the repository root. Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Set `PG_PASSWORD` in the local `.env` file using a text editor. Do not paste it
into source code, terminal commands, or chat. `.env` is ignored by Git;
`.env.example` contains placeholders only.

Run profiling, cleaning, connection verification, and loading in order:

```powershell
py src\inspect_data.py
py src\clean_data.py
py src\config.py
py src\load_data.py
```

The loader uses the existing `kenya_cashflow_db` database only; it does not
create a database. It applies both SQL files, creates `public.transactions` if
needed, verifies that its columns match the cleaned CSV, then replaces rows in
that table in a single transaction. A failed load is rolled back. It reports
the source/database record-count comparison and a few metrics rows. Other
database tables are not dropped or modified.

Run the test suite with:

```powershell
py -m unittest discover -s tests -v
```

## Dataset inspection and cleaning

`python src\inspect_data.py` profiles the raw CSV and writes
`docs/data_quality_report.md`: exact row and column counts, inferred types,
per-column missing counts/percentages, duplicate candidates, dates, amount
statistics, and samples of classification text.

`python src\clean_data.py` writes:

- `data/processed/transactions_cleaned.csv`
- `data/processed/transactions_quarantined.csv`
- `data/processed/cleaning_summary.json`

The cleaner preserves source identifiers and classifications, normalizes dates
and recognized directions, converts KES amounts, and quarantines invalid
critical fields and exact duplicate rows. Reused `trx_id` values alone are not
treated as duplicate transactions. The current cleaned CSV has 465,495 rows and
59 columns, including `source_row_number`.

## PostgreSQL schema and metrics

`sql/01_create_tables.sql` uses the cleaned CSV's actual columns and types.
`trx_id` is not unique in the source; `source_row_number` is the primary key.
`python src\load_data.py` executes this table definition and then
`sql/02_household_metrics.sql`, which creates the view
`public.vw_household_monthly_metrics`. The view groups by `hh_ids` and calendar
month, and includes:

- Inflows, outflows, and net cash flow (inflows minus outflows).
- Earned-income totals and separate amounts for regular employment,
  casual/temporary employment, self-employment, agriculture, and rental income.
- Identified savings deposits/withdrawals and new borrowing/debt repayments.
- Counts of transactions and inflows not classified as earned income.

Earned income is mapped only for exact observed family/type pairs:
regular employment, casual employment (`Casual employment, vibarua` or
`Temporary contractual work`), self-employment, agricultural income, and rental
income. Gifts, borrowing, transfers, savings withdrawals, asset sales,
resources received, non-employment, passthrough income, and ambiguous/unknown
categories are not treated as earned income. Savings and debt measures use
only the exact values in `trx_prx_purpose_fd`; untagged transactions are not
inferred. That field is null for 87.14% of cleaned rows, so these indicators
are partial. See the SQL comments and quality report for these limitations.

Metrics are household-level descriptive aggregates, not individual income or
repayment claims. Review the source categories before using the view for lending
decisions or Power BI.
