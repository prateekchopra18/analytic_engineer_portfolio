# Project 05 — dbt Models (Multi-Source Analytics)

> **Stack**: dbt · Snowflake · Salesforce · Workato  
> **Status**: Production  
> **Warehouse**: Snowflake · Role: `BT_BUSINESS_INTELLIGENCE`

## Overview

Modular dbt project following the **staging → intermediate → marts** layering pattern across multiple source systems — Salesforce CRM, Workato platform usage, and Freshdesk support data. Includes incremental models, schema tests, and auto-generated documentation.

## Project Structure

```
dbt-models/
├── dbt_project.yml
├── profiles.yml.example
├── models/
│   ├── staging/
│   │   ├── salesforce/          # stg_salesforce__*
│   │   ├── workato/             # stg_workato__*
│   │   └── freshdesk/           # stg_freshdesk__*
│   ├── intermediate/            # int_* (cross-source joins)
│   └── marts/
│       ├── core/                # dim_* and fct_* tables
│       └── finance/             # arr, bookings, retention
├── tests/                       # custom singular tests
├── macros/                      # reusable Jinja macros
└── docs/                        # model descriptions
```

## Layer Definitions

### Staging (`stg_`)
- 1:1 with source tables — rename, recast, light cleaning only
- No joins, no business logic
- All columns explicitly selected (no `SELECT *`)
- Materialized as **views**

### Intermediate (`int_`)
- Cross-source joins and enrichment
- Resolves fan-out from denormalized sources
- Materialized as **ephemeral** or **tables**

### Marts (`fct_` / `dim_`)
- Business-facing, aggregated, BI-ready
- Fact tables: grain documented in model header
- Dimension tables: SCD Type 1 (latest state)
- Materialized as **incremental** (fact) or **table** (dim)

## Model Inventory

| Model | Layer | Source | Materialization | Grain |
|-------|-------|--------|-----------------|-------|
| `stg_salesforce__accounts` | staging | Salesforce | view | 1 row / account |
| `stg_salesforce__leads` | staging | Salesforce | view | 1 row / lead |
| `stg_salesforce__opportunities` | staging | Salesforce | view | 1 row / opportunity |
| `stg_workato__recipe_usage` | staging | Workato | view | 1 row / workspace / day |
| `stg_workato__connection_usage` | staging | Workato | view | 1 row / workspace / day |
| `stg_freshdesk__tickets` | staging | Freshdesk | view | 1 row / ticket |
| `int_account_lead_conversion` | intermediate | SF leads + accounts | ephemeral | 1 row / account |
| `dim_accounts` | marts/core | SF accounts | table | 1 row / account |
| `fct_opportunities` | marts/core | SF opps | incremental | 1 row / opportunity |
| `fct_platform_usage` | marts/core | Workato | incremental | 1 row / workspace / day |
| `fct_arr` | marts/finance | SF contracts | incremental | 1 row / contract / month |

## Incremental Strategy

All fact tables use `unique_key` + `updated_at` watermark:

```sql
{{ config(
    materialized = 'incremental',
    unique_key   = 'opportunity_id',
    on_schema_change = 'sync_all_columns'
) }}

{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

## Tests

### Schema Tests (YAML)
- `not_null` on all primary keys and critical dimensions
- `unique` on grain columns
- `accepted_values` on status/type enums
- `relationships` for referential integrity across models

### Custom Singular Tests
- `test_no_negative_arr.sql` — ARR values must be ≥ 0
- `test_conversion_date_after_lead_date.sql` — temporal sanity
- `test_active_recipes_lte_total.sql` — active ≤ total recipes

## Documentation & Lineage

All models documented with:
- Model-level `description` in schema YAML
- Column-level descriptions for all business-facing fields
- `meta` tags for owner, team, and SLA

```bash
dbt docs generate
dbt docs serve   # opens lineage DAG at localhost:8080
```

## Seed Data (Dummy)

All source data uses **fictional dummy records** — no real company data.
Seeds live in `seeds/` and are loaded via `dbt seed`.

| Seed File | Rows | Description |
|-----------|------|-------------|
| `raw_accounts.csv` | 15 | Fictional companies across 10 industries |
| `raw_leads.csv` | 20 | Mix of converted (10) and open (10) leads |
| `raw_opportunities.csv` | 20 | Pipeline across all stages — won, lost, open |
| `raw_contracts.csv` | 15 | Active contracts with TCV and date ranges |
| `raw_platform_usage.csv` | 24 | Monthly workspace usage (Oct–Dec 2024) |
| `raw_support_tickets.csv` | 20 | Tickets across categories, priorities, statuses |

All staging models reference seeds via `{{ ref('raw_*') }}` — no external database connection needed to explore the project locally.

## Running the Project

```bash
# Install dependencies
pip install dbt-snowflake

# Configure profile
cp profiles.yml.example ~/.dbt/profiles.yml
# edit with your Snowflake credentials

# Load dummy seed data first
dbt seed

# Full refresh
dbt run --full-refresh

# Incremental run (daily)
dbt run

# Tests only
dbt test

# Specific model + downstream
dbt run --select fct_opportunities+

# Generate & serve docs
dbt docs generate && dbt docs serve
```

## Files

```
dbt-models/
├── README.md
├── dbt_project.yml
├── profiles.yml.example
├── models/
│   ├── staging/
│   │   ├── salesforce/
│   │   │   ├── stg_salesforce__accounts.sql
│   │   │   ├── stg_salesforce__leads.sql
│   │   │   ├── stg_salesforce__opportunities.sql
│   │   │   └── schema.yml
│   │   ├── workato/
│   │   │   ├── stg_workato__recipe_usage.sql
│   │   │   ├── stg_workato__connection_usage.sql
│   │   │   └── schema.yml
│   │   └── freshdesk/
│   │       ├── stg_freshdesk__tickets.sql
│   │       └── schema.yml
│   ├── intermediate/
│   │   ├── int_account_lead_conversion.sql
│   │   └── schema.yml
│   └── marts/
│       ├── core/
│       │   ├── dim_accounts.sql
│       │   ├── fct_opportunities.sql
│       │   ├── fct_platform_usage.sql
│       │   └── schema.yml
│       └── finance/
│           ├── fct_arr.sql
│           └── schema.yml
├── tests/
│   ├── test_no_negative_arr.sql
│   ├── test_conversion_date_after_lead_date.sql
│   └── test_active_recipes_lte_total.sql
├── macros/
│   ├── generate_schema_name.sql
│   └── cents_to_dollars.sql
└── docs/
    └── overview.md
```
