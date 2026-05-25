-- test_active_recipes_lte_total.sql
-- Fails if active_recipes > total_recipes for any workspace/day.
-- Active recipes is a subset of total — this catches upstream ETL issues
-- in the Workato usage pipeline.

SELECT
    workspace_id,
    snapshot_date,
    active_recipes,
    total_recipes
FROM {{ ref('fct_platform_usage') }}
WHERE active_recipes > total_recipes
