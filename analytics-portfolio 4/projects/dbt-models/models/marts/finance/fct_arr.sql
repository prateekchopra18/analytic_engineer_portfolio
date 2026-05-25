-- fct_arr.sql
-- Grain: 1 row per contract per active month
-- Materialization: incremental (unique_key = contract_id + arr_month)
-- Sources: stg_salesforce__contracts, dim_accounts

{{
    config(
        materialized     = 'incremental',
        unique_key       = ['contract_id', 'arr_month'],
        on_schema_change = 'sync_all_columns'
    )
}}

WITH contracts AS (
    SELECT * FROM {{ ref('stg_salesforce__contracts') }}

    {% if is_incremental() %}
        WHERE updated_at > (
            SELECT DATEADD('day', -{{ var('incremental_lookback_days') }}, MAX(updated_at))
            FROM {{ this }}
        )
    {% endif %}
),

-- Generate one row per month the contract is active
date_spine AS (
    {{ dbt_utils.date_spine(
        datepart   = "month",
        start_date = "cast('2020-01-01' as date)",
        end_date   = "cast(dateadd('month', 1, current_date()) as date)"
    ) }}
),

contract_months AS (
    SELECT
        c.contract_id,
        c.account_id,
        c.contract_name,
        c.contract_status,
        c.start_date,
        c.end_date,
        c.total_contract_value,
        -- Monthly ARR = TCV / contract duration in months
        DIV0(
            c.total_contract_value,
            DATEDIFF('month', c.start_date, c.end_date)
        )                           AS monthly_arr,
        d.date_month                AS arr_month
    FROM contracts      c
    JOIN date_spine     d
        ON  d.date_month >= DATE_TRUNC('month', c.start_date)
        AND d.date_month <  DATE_TRUNC('month', c.end_date)
    WHERE c.contract_status IN ('Activated', 'Signed')
),

accounts AS (
    SELECT account_id, account_name, account_type, industry
    FROM {{ ref('dim_accounts') }}
),

final AS (
    SELECT
        -- Keys
        cm.contract_id,
        cm.arr_month,
        cm.account_id,

        -- Account context
        a.account_name,
        a.account_type,
        a.industry,

        -- Contract dimensions
        cm.contract_name,
        cm.contract_status,
        cm.start_date,
        cm.end_date,

        -- Measures
        cm.monthly_arr              AS arr_usd,
        cm.total_contract_value,

        -- Derived flags
        cm.arr_month = DATE_TRUNC('month', cm.start_date) AS is_new_arr,
        cm.arr_month = DATE_TRUNC('month',
            DATEADD('month', -1, cm.end_date))            AS is_churning_arr,

        -- Metadata
        CURRENT_TIMESTAMP()         AS dbt_loaded_at

    FROM contract_months cm
    LEFT JOIN accounts a ON a.account_id = cm.account_id
)

SELECT * FROM final
