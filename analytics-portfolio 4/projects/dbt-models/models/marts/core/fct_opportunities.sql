-- fct_opportunities.sql
-- Grain: 1 row per opportunity
-- Materialization: incremental (unique_key = opportunity_id)
-- Sources: stg_salesforce__opportunities, dim_accounts

{{
    config(
        materialized     = 'incremental',
        unique_key       = 'opportunity_id',
        on_schema_change = 'sync_all_columns'
    )
}}

WITH opportunities AS (
    SELECT * FROM {{ ref('stg_salesforce__opportunities') }}

    {% if is_incremental() %}
        WHERE updated_at > (
            SELECT DATEADD('day', -{{ var('incremental_lookback_days') }}, MAX(updated_at))
            FROM {{ this }}
        )
    {% endif %}
),

accounts AS (
    SELECT
        account_id,
        account_name,
        account_type,
        industry
    FROM {{ ref('dim_accounts') }}
),

lead_conversion AS (
    SELECT
        converted_opportunity_id,
        lead_id,
        lead_source,
        lead_type           AS opportunity_from_lead_type
    FROM {{ ref('int_account_lead_conversion') }}
    WHERE converted_opportunity_id IS NOT NULL
),

final AS (
    SELECT
        -- Keys
        o.opportunity_id,
        o.account_id,

        -- Account context
        a.account_name,
        a.account_type      AS opportunity_from_account_type,
        a.industry,

        -- Lead attribution
        lc.lead_id,
        lc.lead_source,
        lc.opportunity_from_lead_type,

        -- Opportunity dimensions
        o.opportunity_name,
        o.stage_name,
        o.is_won,
        o.is_closed,
        o.close_date,
        o.created_at        AS opportunity_created_at,

        -- Measures
        o.amount            AS arr_usd,

        -- Derived
        DATEDIFF('day', o.created_at, o.close_date) AS days_to_close,
        CASE
            WHEN o.is_won  THEN 'Won'
            WHEN o.is_closed AND NOT o.is_won THEN 'Lost'
            ELSE 'Open'
        END                 AS opportunity_status,

        -- Metadata
        o.updated_at,
        CURRENT_TIMESTAMP() AS dbt_loaded_at

    FROM opportunities  o
    LEFT JOIN accounts      a  ON a.account_id             = o.account_id
    LEFT JOIN lead_conversion lc ON lc.converted_opportunity_id = o.opportunity_id
)

SELECT * FROM final
