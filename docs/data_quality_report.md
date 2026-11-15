# Raw Data Quality Report

- **Source file:** `diaries_transactions_all.csv`
- **Rows:** 483,949
- **Columns:** 58
- **Data types:** inferred from the first 1,000 rows.

## Source columns, inferred types, and missing values

| Column | Sample dtype | Null count | Null percent |
| --- | --- | --- | --- |
| hh_ids | str | 0 | 0.00% |
| unique_hhs | float64 | 483,651 | 99.94% |
| first_trx_date_hh | str | 0 | 0.00% |
| last_trx_date_hh | str | 0 | 0.00% |
| tot_hh_daysofobs | int64 | 0 | 0.00% |
| tot_hh_monthsofobs | int64 | 0 | 0.00% |
| interview_designation | str | 268 | 0.06% |
| int_date | str | 0 | 0.00% |
| int_month | int64 | 0 | 0.00% |
| int_year | int64 | 0 | 0.00% |
| int_yr_mo | str | 0 | 0.00% |
| first_int_date | str | 0 | 0.00% |
| account_ids | str | 0 | 0.00% |
| unique_accnts | float64 | 474,403 | 98.03% |
| m_ids_owner | str | 0 | 0.00% |
| unique_hm_owner | float64 | 483,279 | 99.86% |
| account_bsheet_desig | str | 406,879 | 84.07% |
| account_startclose_balance | str | 477,007 | 98.57% |
| account_formal | str | 406,879 | 84.07% |
| account_liquid | str | 434,028 | 89.68% |
| first_trx_date_acc | str | 0 | 0.00% |
| last_trx_date_acc | str | 0 | 0.00% |
| tot_acc_daysofobs | int64 | 0 | 0.00% |
| tot_acc_monthsofobs | int64 | 0 | 0.00% |
| trx_id | int64 | 0 | 0.00% |
| m_ids_trx | str | 0 | 0.00% |
| trx_date | str | 0 | 0.00% |
| trx_month | int64 | 0 | 0.00% |
| trx_year | int64 | 0 | 0.00% |
| trx_yr_mo | str | 0 | 0.00% |
| trx_dq_round | float64 | 1,302 | 0.27% |
| trx_stdtime_days_hh | int64 | 0 | 0.00% |
| trx_stdtime_mnths_hh | int64 | 0 | 0.00% |
| trx_stdtime_days_acc | int64 | 0 | 0.00% |
| trx_stdtime_mnths_acc | int64 | 0 | 0.00% |
| trx_class_code | str | 0 | 0.00% |
| trx_class_desc | str | 0 | 0.00% |
| trx_family_code | str | 0 | 0.00% |
| trx_family_desc | str | 0 | 0.00% |
| trx_type_code | int64 | 0 | 0.00% |
| trx_type_desc | str | 0 | 0.00% |
| trx_prx_purpose | str | 0 | 0.00% |
| trx_prx_purpose_fd | str | 423,999 | 87.61% |
| trx_fee | float64 | 406,879 | 84.07% |
| trx_bsheet_direction | str | 412,753 | 85.29% |
| trx_mode_code | float64 | 7,657 | 1.58% |
| trx_mode_desc | str | 7,657 | 1.58% |
| trx_place_incommunity | float64 | 26,246 | 5.42% |
| trx_distance_km | float64 | 26,451 | 5.47% |
| trx_outlet | str | 147,886 | 30.56% |
| trx_direction | str | 14,912 | 3.08% |
| trx_value_kes | int64 | 519 | 0.11% |
| trx_value_usd | float64 | 519 | 0.11% |
| ddd_gift | int64 | 0 | 0.00% |
| trx_inkind_units | float64 | 470,525 | 97.23% |
| trx_inkind_value_usd | float64 | 471,151 | 97.36% |
| trx_inkind_value_kes | float64 | 471,151 | 97.36% |
| trx_stdtime_mnths_hh_nr | float64 | 0 | 0.00% |

## Duplicate review

- Exact row fingerprint duplicate candidates: 3,060.
- Repeated transaction IDs: 258,164 rows after each ID's first occurrence, across 35,279 IDs. Repeated IDs are not assumed to be duplicate transactions.
- Fingerprint matches are candidates and must be reviewed before removal.

## Schema notes

- All expected profiling fields are present. The prompt's `trx_family_de` label corresponds to the actual CSV column `trx_family_desc`.

## Key data-quality risks

- Missing transaction direction: 14,912 rows. These cannot safely be classified as inflow or outflow.
- Missing KES amount: 519 rows. These cannot be used in amount-based indicators.
- Duplicate/key ambiguity: 3,060 exact-row fingerprint candidates and 258,164 rows after first occurrence of a reused transaction ID. Repeated IDs alone are not proof of duplicate transactions.

## Date range

- Earliest parsed transaction: 2012-08-01
- Latest parsed transaction: 2013-12-31
- Invalid non-null date values: 0

## Direction counts

- Inflow: 100,736
- Missing: 14,912
- Outflow: 368,301

## Household and category counts

- Unique households: 298
- Unique `trx_family_desc` values: 43
- Unique `trx_type_desc` values: 182

## KES amount summary

- Non-null values that could not be converted to numeric: 0
| Statistic | KES / count |
| --- | --- |
| valid count | 483,430.00 |
| sum kes | 316,512,648.00 |
| mean kes | 654.72 |
| std kes | 5,453.24 |
| min kes | -25,950.00 |
| 25 percentile kes | 20.00 |
| median kes | 50.00 |
| 75 percentile kes | 230.00 |
| max kes | 1,200,000.00 |

## Free-text and classification samples

Samples are raw values; review inconsistent spelling, casing, and overlapping meanings before creating mappings.

Observed examples include mixed casing (`CLOSING BALANCE` versus `Cash`) and inconsistent punctuation (`Cash lost , stolen, missing`). These classification fields should be mapped only after reviewing the source definitions.

### `trx_family_desc`

- Unique values: 43
- Rows with leading/trailing whitespace: 0
- Sample values: `Informal P2P`; `Cash`; `Informal group`; `Informal savings: keep money at home`; `Communications`; `Mobile Money`; `Self-employment`; `Food`; `Supplier credit`; `Formal loan`

### `trx_type_desc`

- Unique values: 182
- Rows with leading/trailing whitespace: 0
- Sample values: `Friends and Family: Lending`; `Cash on hand now`; `Borrowing from an informal Group`; `Keeping Money (Cash) at Home`; `Pre-paid phone credit and data bundles`; `Mobile Money`; `Self-employment`; `Other food/beverage purchases (small things at shop, bus station, on street)`; `Welfare Group`; `Cash lost , stolen, missing`

### `trx_prx_purpose`

- Unique values: 117
- Rows with leading/trailing whitespace: 0
- Sample values: `7. Closing Balance--End of last DQ`; `Cash on hand now (end of period)`; `3. Withdrawals`; `Purchases`; `1. Starting balance (today)`; `3. Stock purchases`; `3. Closing Balance--End of last DQ`; `Cash lost, stolen, or otherwise missing`; `INCREASE--Unexplained balance adjustment`; `6. Closing Balance--End of last DQ`

### `trx_prx_purpose_fd`

- Unique values: 4
- Rows with leading/trailing whitespace: 0
- Sample values: `Withdrawal on financial asset`; `Deposit on financial asset`; `New borrowing on financial liability`; `Repayment on financial liability`

### `trx_mode_desc`

- Unique values: 19
- Rows with leading/trailing whitespace: 0
- Sample values: `CLOSING BALANCE`; `Cash`; `STARTING BALANCE`; `Purchase on credit/arrears`; `Automatic`; `Mobile money transfer (M-PESA, Airtel Money, Orange Money, Yu Cash, Tangaza, etc)`; `Transfer into bank, SACCO, or MFI account`; `Airtime exchange, sambaza`; `In-kind (trade, good, service--NOT MONEY)`; `Looking for work or business opportunities`

### `trx_place_incommunity`

- Unique values: 2
- Rows with leading/trailing whitespace: 0
- Sample values: `0`; `1`

### `trx_outlet`

- Unique values: 280
- Rows with leading/trailing whitespace: 0
- Sample values: `02=Outdoor kiosk or stall`; `03=Duka or other small shop (butchery, chemist, etc.)`; `06=Direct deposit, payroll deduction, or standing order`; `04=Mobile phone only`; `11=Matatu, bus, piki piki, other transport provider`; `09=Individual person, household, farm`; `13=Private individual or household`; `01=Bank, MFI, SACCO, insurance branch`; `01=Hawker--no structure`; `08=Restaurant, bar, hotel, cyber`

## Cleaning decisions

- Preserve the original raw CSV unchanged.
- Standardize column names and trim surrounding whitespace.
- Parse transaction dates and KES amounts without inventing missing values.
- Standardize only recognized `Inflow` / `Outflow` values.
- Quarantine rows missing a household, parseable date, numeric amount, or recognized direction.
- Quarantine exact duplicate records after the first occurrence; do not deduplicate on `trx_id` alone.
- Preserve household, member, account, transaction, and classification identifiers in outputs.

## Cleaning results

- Source rows: 483,949
- Clean rows: 465,495
- Quarantined rows: 18,454
- Rows affected by each reason (reasons can overlap):
  - missing_household_id: 0
  - invalid_transaction_date: 0
  - missing_or_non_numeric_amount: 519
  - missing_or_unrecognized_direction: 14,912
  - exact_duplicate_record: 3,060

Outputs: `transactions_cleaned.csv`, `transactions_quarantined.csv`, and `cleaning_summary.json`.

## Household metric classification limits

The PostgreSQL household-month view uses `hh_ids` and `trx_date`. Earned income is limited to exact, reviewed family/type pairs for regular employment, casual/temporary employment, self-employment, agriculture, and rental income.

Borrowing, gifts, transfers, savings withdrawals, asset sales, resources received, non-employment, passthrough income, and ambiguous or unknown categories are not counted as earned income. Savings deposits/withdrawals and borrowing/repayments are counted only when explicitly tagged in `trx_prx_purpose_fd`; untagged transactions are not inferred. This field is missing for 87.61% of raw rows, so these indicators are partial.

## Scope and limitations

This historical household dataset supports descriptive financial profiling only. It does not provide verified loan performance outcomes, and household records must not be interpreted as a specific individual's complete finances. The project does not produce a validated credit score or default prediction.
