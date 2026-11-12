import pandas as pd
import numpy as np

# Load raw data
df = pd.read_csv("../data/raw_data/diaries_transactions_all.csv")

# -------------------------------------------------------------
# RULE 1: Drop columns that are 100% empty (entire column is NaN)
# -------------------------------------------------------------
# Check initial shape
print(f"Initial columns count: {df.shape[1]}")

# Drop columns where ALL values are null
df = df.dropna(axis=1, how='all')

print(f"Columns after dropping completely empty ones: {df.shape[1]}")


# -------------------------------------------------------------
# RULE 2: Fill non-critical categorical columns with explicit defaults
# -------------------------------------------------------------
# If sub_category or notes are empty, don't leave them as NaN (causes issues in SQL/PostgreSQL)
df['sub_category'] = df['sub_category'].fillna('Unspecified')
df['notes'] = df['notes'].fillna('No description recorded')

# If payment_mode is missing, check if cash was the default in the field
df['payment_mode'] = df['payment_mode'].fillna('cash')


# -------------------------------------------------------------
# RULE 3: Quarantine or drop rows missing NON-NEGOTIABLE fields
# -------------------------------------------------------------
# Columns required to answer the core business question
non_negotiable_cols = ['respondent_id', 'date', 'amount']

# Count how many bad rows exist
missing_critical_count = df[non_negotiable_cols].isnull().any(axis=1).sum()
print(f"Rows missing critical financial fields: {missing_critical_count}")

# Quarantine bad rows to a separate DataFrame (or log file) for auditing
quarantined_rows = df[df[non_negotiable_cols].isnull().any(axis=1)]

# Keep only valid rows in your main clean table pipeline
df_clean = df.dropna(subset=non_negotiable_cols).copy()