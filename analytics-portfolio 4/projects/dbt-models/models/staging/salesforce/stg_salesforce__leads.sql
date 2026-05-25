-- stg_salesforce__leads.sql
-- Grain: 1 row per lead
-- Source: seeds/raw_leads.csv

WITH source AS (
    SELECT * FROM {{ ref('raw_leads') }}
),

renamed AS (
    SELECT
        lead_id,
        account_id,
        is_converted,
        converted_opportunity_id,
        lead_source,
        lead_type,
        lead_created_at,
        converted_at
    FROM source
)

SELECT * FROM renamed
