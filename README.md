
# Kenya Household Cash-Flow Data Pipeline

## Project Overview

This project develops a data engineering pipeline using the Kenya Financial Diaries dataset.

The objective is to extract, clean, transform and store household financial transactions in PostgreSQL and provide insights into household cash-flow patterns.

## Business Problem

Low-income households experience fluctuations in income and expenditure. This project aims to help financial inclusion analysts and NGO programme managers identify unusual changes in household cash flow.

## Technology Stack

- Python
- Pandas
- PostgreSQL
- SQL
- Git and GitHub

## Project Structure

```text
kenya_cashflow_pipeline/
│
├── data/
│   ├── raw_data/
│   └── processed_data/
│
├── src/
├── sql/
├── docs/
├── dashboard/
├── .gitignore
└── README.md
```

## Pipeline Architecture

Raw Data → Extraction → Transformation → PostgreSQL → Dashboard

## Project Status

Currently in development.
