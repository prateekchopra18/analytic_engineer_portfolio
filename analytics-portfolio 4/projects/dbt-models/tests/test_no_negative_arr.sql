-- test_no_negative_arr.sql
-- Fails if any contract has a negative ARR value.
-- ARR must always be >= 0; negative values indicate a data quality issue
-- in Salesforce contract amounts.

SELECT
    contract_id,
    arr_month,
    arr_usd
FROM {{ ref('fct_arr') }}
WHERE arr_usd < 0
