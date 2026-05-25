-- stg_salesforce__opportunities.sql
-- Grain: 1 row per opportunity
-- Source: seeds/raw_opportunities.csv

WITH source AS (
    SELECT * FROM {{ ref('raw_opportunities') }}
),

renamed AS (
    SELECT
        opportunity_id,
        account_id,
        opportunity_name,
        stage_name,
        is_won,
        is_closed,
        close_date,
        amount,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed
