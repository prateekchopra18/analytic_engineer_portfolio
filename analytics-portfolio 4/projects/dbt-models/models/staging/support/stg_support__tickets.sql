-- stg_support__tickets.sql
-- Grain: 1 row per support ticket
-- Source: seeds/raw_support_tickets.csv

WITH source AS (
    SELECT * FROM {{ ref('raw_support_tickets') }}
),

renamed AS (
    SELECT
        ticket_id,
        account_id,
        subject,
        category,
        priority,
        status,
        created_at,
        first_response_at,
        resolved_at,
        csat_score,
        updated_at,

        -- Derived
        DATEDIFF('minute', created_at, first_response_at)   AS first_response_minutes,
        DATEDIFF('hour',   created_at, resolved_at)         AS resolution_hours,
        CASE WHEN status = 'Resolved' THEN TRUE ELSE FALSE END AS is_resolved

    FROM source
)

SELECT * FROM renamed
