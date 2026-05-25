-- ============================================================
-- OBT Salesforce Model
-- Author: Prateek Chopra (PRATEEKCHOPRA)
-- Role: BT_BUSINESS_INTELLIGENCE
-- Database: BT_DEV.PCHOPRA
-- ============================================================

CREATE OR REPLACE TABLE BT_DEV.PCHOPRA.OBT_SALESFORCE AS

WITH accounts AS (
    SELECT
        ACCOUNTID,
        ACCOUNT_NAME,
        ACCOUNT_TYPE,
        INDUSTRY,
        ANNUAL_REVENUE,
        CREATED_DATE         AS ACCOUNT_CREATED_DATE
    FROM SALESFORCE.ACCOUNT
    WHERE IS_DELETED = FALSE
),

leads AS (
    SELECT
        LEADID,
        CONVERTEDACCOUNTID,
        CONVERTEDOPPORTUNITYID,
        ISCONVERTED            AS ACCOUNT_TO_LEAD_CONVERSION,
        LEAD_SOURCE,
        LEAD_TYPE              AS OPPORTUNITY_FROM_LEAD_TYPE,
        CREATED_DATE           AS LEAD_CREATED_DATE,
        CONVERTED_DATE
    FROM SALESFORCE.LEAD
    WHERE IS_DELETED = FALSE
),

opportunities AS (
    SELECT
        OPPORTUNITYID,
        ACCOUNTID,
        OPPORTUNITY_NAME,
        OPPORTUNITY_TYPE       AS OPPORTUNITY_FROM_ACCOUNT_TYPE,
        STAGE_NAME,
        CLOSE_DATE,
        AMOUNT                 AS ARR,
        IS_WON,
        CREATED_DATE           AS OPP_CREATED_DATE
    FROM SALESFORCE.OPPORTUNITY
    WHERE IS_DELETED = FALSE
),

contracts AS (
    SELECT
        CONTRACTID,
        ACCOUNTID,
        CONTRACT_NAME,
        CONTRACT_STATUS,
        START_DATE,
        END_DATE,
        TOTAL_CONTRACT_VALUE
    FROM SALESFORCE.CONTRACT
    WHERE IS_DELETED = FALSE
)

SELECT
    -- Account grain
    a.ACCOUNTID,
    a.ACCOUNT_NAME,
    a.ACCOUNT_TYPE,
    a.INDUSTRY,
    a.ANNUAL_REVENUE,
    a.ACCOUNT_CREATED_DATE,

    -- Lead dimensions
    l.LEADID,
    l.ACCOUNT_TO_LEAD_CONVERSION,
    l.LEAD_SOURCE,
    l.OPPORTUNITY_FROM_LEAD_TYPE,
    l.LEAD_CREATED_DATE,
    l.CONVERTED_DATE,

    -- Opportunity dimensions
    o.OPPORTUNITYID,
    l.CONVERTEDOPPORTUNITYID,
    o.OPPORTUNITY_NAME,
    o.OPPORTUNITY_FROM_ACCOUNT_TYPE,
    o.STAGE_NAME,
    o.IS_WON,
    o.CLOSE_DATE,
    o.ARR,
    o.OPP_CREATED_DATE,

    -- Contract dimensions
    c.CONTRACTID,
    c.CONTRACT_NAME,
    c.CONTRACT_STATUS,
    c.START_DATE             AS CONTRACT_START_DATE,
    c.END_DATE               AS CONTRACT_END_DATE,
    c.TOTAL_CONTRACT_VALUE,

    -- Metadata
    CURRENT_TIMESTAMP()      AS LAST_REFRESHED_AT

FROM accounts a
LEFT JOIN leads       l ON l.CONVERTEDACCOUNTID  = a.ACCOUNTID
LEFT JOIN opportunities o ON o.ACCOUNTID          = a.ACCOUNTID
LEFT JOIN contracts   c ON c.ACCOUNTID            = a.ACCOUNTID;
