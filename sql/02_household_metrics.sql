-- Earned income is limited to exact, reviewed employment/agriculture/rental
-- category pairs. Other inflows are not assumed to be earnings.
-- Savings and debt indicators use explicit trx_prx_purpose_fd values only;
-- missing purpose classifications are not inferred.
CREATE OR REPLACE VIEW public.vw_household_monthly_metrics AS
WITH classified_transactions AS (
    SELECT
        hh_ids,
        trx_date,
        trx_direction,
        trx_value_kes,
        trx_prx_purpose_fd,
        CASE
            WHEN trx_direction = 'Inflow'
                 AND trx_family_desc = 'Regular employment'
                 AND trx_type_desc = 'Regular employment'
                THEN 'Regular employment'
            WHEN trx_direction = 'Inflow'
                 AND trx_family_desc = 'Casual/temp employment'
                 AND trx_type_desc IN (
                     'Casual employment, vibarua',
                     'Temporary contractual work'
                 )
                THEN 'Casual/temp employment'
            WHEN trx_direction = 'Inflow'
                 AND trx_family_desc = 'Self-employment'
                 AND trx_type_desc = 'Self-employment'
                THEN 'Self-employment'
            WHEN trx_direction = 'Inflow'
                 AND trx_family_desc = 'Agriculture'
                 AND trx_type_desc = 'Agricultural Income'
                THEN 'Agriculture'
            WHEN trx_direction = 'Inflow'
                 AND trx_family_desc = 'Rental or other'
                 AND trx_type_desc = 'Rental Income'
                THEN 'Rental income'
            ELSE NULL
        END AS earned_income_source
    FROM public.transactions
)
SELECT
    hh_ids AS household_id,
    DATE_TRUNC('month', trx_date)::date AS month_start,
    COALESCE(
        SUM(trx_value_kes) FILTER (WHERE trx_direction = 'Inflow'),
        0
    ) AS total_inflows_kes,
    COALESCE(
        SUM(trx_value_kes) FILTER (WHERE trx_direction = 'Outflow'),
        0
    ) AS total_outflows_kes,
    COALESCE(
        SUM(trx_value_kes) FILTER (WHERE trx_direction = 'Inflow'),
        0
    ) - COALESCE(
        SUM(trx_value_kes) FILTER (WHERE trx_direction = 'Outflow'),
        0
    ) AS net_cash_flow_kes,
    COALESCE(
        SUM(trx_value_kes) FILTER (WHERE earned_income_source IS NOT NULL),
        0
    ) AS earned_income_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (WHERE earned_income_source = 'Regular employment'),
        0
    ) AS regular_employment_income_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (WHERE earned_income_source = 'Casual/temp employment'),
        0
    ) AS casual_employment_income_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (WHERE earned_income_source = 'Self-employment'),
        0
    ) AS self_employment_income_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (WHERE earned_income_source = 'Agriculture'),
        0
    ) AS agricultural_income_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (WHERE earned_income_source = 'Rental income'),
        0
    ) AS rental_income_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (
                WHERE trx_direction = 'Inflow'
                  AND earned_income_source IS NULL
            ),
        0
    ) AS other_inflows_not_classified_as_earned_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (
                WHERE trx_direction = 'Outflow'
                  AND trx_prx_purpose_fd = 'Deposit on financial asset'
            ),
        0
    ) AS identified_savings_deposits_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (
                WHERE trx_direction = 'Inflow'
                  AND trx_prx_purpose_fd = 'Withdrawal on financial asset'
            ),
        0
    ) AS identified_savings_withdrawals_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (
                WHERE trx_direction = 'Inflow'
                  AND trx_prx_purpose_fd = 'New borrowing on financial liability'
            ),
        0
    ) AS identified_new_borrowing_kes,
    COALESCE(
        SUM(trx_value_kes)
            FILTER (
                WHERE trx_direction = 'Outflow'
                  AND trx_prx_purpose_fd = 'Repayment on financial liability'
            ),
        0
    ) AS identified_debt_repayments_kes,
    COUNT(*) AS transaction_count,
    COUNT(*) FILTER (
        WHERE trx_direction = 'Inflow' AND earned_income_source IS NULL
    ) AS inflow_transactions_not_classified_as_earned,
    COUNT(*) FILTER (WHERE trx_prx_purpose_fd IS NOT NULL)
        AS purpose_classified_transaction_count
FROM classified_transactions
GROUP BY hh_ids, DATE_TRUNC('month', trx_date)::date;
