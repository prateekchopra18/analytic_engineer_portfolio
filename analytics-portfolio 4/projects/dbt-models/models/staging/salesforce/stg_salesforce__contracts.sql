-- stg_salesforce__contracts.sql
-- Grain: 1 row per contract
-- Source: seeds/raw_contracts.csv

WITH source AS (
    SELECT * FROM {{ ref('raw_contracts') }}
),

renamed AS (
    SELECT
        contract_id,
        account_id,
        opportunity_id,
        contract_name,
        contract_status,
        start_date,
        end_date,
        total_contract_value,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed
