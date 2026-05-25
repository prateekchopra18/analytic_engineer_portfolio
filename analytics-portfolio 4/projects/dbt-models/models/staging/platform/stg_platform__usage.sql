-- stg_platform__usage.sql
-- Grain: 1 row per workspace per snapshot month
-- Source: seeds/raw_platform_usage.csv

WITH source AS (
    SELECT * FROM {{ ref('raw_platform_usage') }}
),

renamed AS (
    SELECT
        workspace_id,
        account_id,
        snapshot_date,
        active_recipes,
        total_recipes,
        active_connections,
        total_connections,
        recipe_runs,
        updated_at
    FROM source
)

SELECT * FROM renamed
