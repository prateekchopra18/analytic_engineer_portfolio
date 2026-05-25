-- stg_salesforce__accounts.sql
-- Grain: 1 row per account
-- Source: seeds/raw_accounts.csv

WITH source AS (
    SELECT * FROM {{ ref('raw_accounts') }}
),

renamed AS (
    SELECT
        account_id,
        account_name,
        account_type,
        industry,
        employee_count,
        billing_country,
        billing_state,
        annual_revenue_usd,
        owner_id,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed
