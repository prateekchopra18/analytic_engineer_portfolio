# Project 01 — Salesforce OBT Analytics

> **Stack**: Snowflake · SQL · Sigma  
> **Status**: Production  
> **Table**: `BT_DEV.PCHOPRA.OBT_SALESFORCE`

## Overview

Designed and implemented a **One Big Table (OBT)** pattern for Salesforce data, consolidating leads, opportunities, accounts, contracts, and line items into a single denormalized analytical surface. Enables self-serve analytics without complex joins.

## Key Metrics Delivered

| Metric | Value |
|--------|-------|
| Total Accounts | ~136,248 |
| Accounts with Converted Leads | ~56,741 |
| Accounts with Leads + Opportunities | ~18,578 |
| Columns in OBT schema | 27 |

## Schema Design

```sql
-- Core dimensions in OBT_SALESFORCE
SELECT
    -- Account dimensions
    ACCOUNTID,
    ACCOUNT_NAME,
    ACCOUNT_TYPE,

    -- Lead dimensions
    LEADID,
    ACCOUNT_TO_LEAD_CONVERSION,     -- custom conversion flag
    OPPORTUNITY_FROM_LEAD_TYPE,

    -- Opportunity dimensions
    CONVERTEDOPPORTUNITYID,
    OPPORTUNITY_FROM_ACCOUNT_TYPE,

    -- Contract dimensions
    CONTRACT_NAME,
    CONTRACT_STATUS,

    -- Measures
    ARR,
    TOTAL_CONTRACT_VALUE

FROM BT_DEV.PCHOPRA.OBT_SALESFORCE;
```

## Key Design Decisions

### Why OBT?
- Eliminates multi-hop joins across 6+ Salesforce objects
- Enables `COUNT(DISTINCT ...)` aggregations without fan-out duplication
- Single semantic surface for Sigma dashboard consumption

### Handling Row Duplication
The denormalized structure produces duplicate rows at the account level. All aggregations use:
```sql
COUNT(DISTINCT ACCOUNTID)       -- NOT COUNT(*)
COUNT(DISTINCT CONVERTEDOPPORTUNITYID)
SUM(DISTINCT ARR)               -- with dedup subquery
```

## Sample Queries

### Accounts with Converted Leads
```sql
SELECT COUNT(DISTINCT ACCOUNTID) AS accounts_with_converted_leads
FROM BT_DEV.PCHOPRA.OBT_SALESFORCE
WHERE ACCOUNT_TO_LEAD_CONVERSION = TRUE;
-- Result: ~56,741
```

### Lead-to-Opportunity Conversion Funnel
```sql
SELECT
    COUNT(DISTINCT ACCOUNTID)                           AS total_accounts,
    COUNT(DISTINCT CASE WHEN LEADID IS NOT NULL
        THEN ACCOUNTID END)                             AS accounts_with_leads,
    COUNT(DISTINCT CASE WHEN LEADID IS NOT NULL
        AND CONVERTEDOPPORTUNITYID IS NOT NULL
        THEN ACCOUNTID END)                             AS converted_to_opp
FROM BT_DEV.PCHOPRA.OBT_SALESFORCE;
```

## Files

```
snowflake-analytics/
├── README.md
├── sql/
│   ├── obt_salesforce_model.sql      # Full OBT definition
│   ├── lead_conversion_analysis.sql  # Funnel queries
│   └── arr_metrics.sql               # ARR aggregations
└── docs/
    └── schema_reference.md           # Column definitions
```
