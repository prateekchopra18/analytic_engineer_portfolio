-- test_conversion_date_after_lead_date.sql
-- Fails if any lead has a converted_date before its created_date.
-- Temporal sanity check — conversion can never precede lead creation.

SELECT
    lead_id,
    lead_created_at,
    converted_at
FROM {{ ref('stg_salesforce__leads') }}
WHERE is_converted = TRUE
  AND converted_at < lead_created_at
