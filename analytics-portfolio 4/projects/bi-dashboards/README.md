# Project 04 — BI Dashboard Suite

> **Stack**: Sigma · Snowflake · Workato  
> **Status**: Production  
> **Role**: BT_BUSINESS_INTELLIGENCE

## Overview

Suite of executive and operational dashboards built on Sigma, powered by Snowflake OBT models. Covers ARR tracking, pipeline health, Workato platform adoption, and CS/CX metrics.

## Dashboard Inventory

### 1. ARR & Bookings Dashboard
**Audience**: Revenue leadership, Finance  
**Refresh**: Daily  
**Source**: `BT_DEV.PCHOPRA.OBT_SALESFORCE`

Key metrics:
- Net New ARR (nswARR) — Plan vs Actual
- ARR by segment (SMB / Mid-Market / Enterprise)
- Quarterly bookings waterfall
- Lead-to-close conversion funnel

### 2. Workato Platform Adoption
**Audience**: Product, CS, Leadership  
**Refresh**: Daily  
**Source**: `DATA_GENIE.WORKATO_USAGE.*`

Key metrics:
- Active recipe users (MAU/WAU/DAU)
- Active connection counts by workspace
- Recipe run volume trends
- Top connectors by usage

### 3. Pipeline Health Monitor
**Audience**: Sales leadership, RevOps  
**Refresh**: Daily  
**Source**: `BT_DEV.PCHOPRA.OBT_SALESFORCE`

Key metrics:
- Open pipeline by stage
- Pipeline coverage ratio (vs quota)
- Average days in stage
- At-risk opportunities (no activity > 14 days)

### 4. CS/CX Ticket Analytics
**Audience**: CS leadership  
**Refresh**: Daily  
**Source**: Freshdesk → Workato → Snowflake

Key metrics:
- Ticket volume by category
- First response time (P50/P95)
- CSAT score trends
- Escalation rate

## Design Principles

```
1. Single source of truth    →  All dashboards from OBT models
2. Self-serve first          →  Sigma for ad-hoc exploration
3. COUNT(DISTINCT ...)       →  Always, due to OBT fan-out
4. Semantic layer contract   →  Column names stable across versions
```

## Semantic Layer Strategy

Built and maintained semantic models in Data Genie (MCP-based) that expose clean, business-friendly column names to Sigma. Validated against `extract_yaml_file` tool for full 27-column coverage.

Key verified columns:
- `ACCOUNT_TO_LEAD_CONVERSION` — lead funnel analysis
- `OPPORTUNITY_FROM_ACCOUNT_TYPE` — segmentation
- `CONTRACT_STATUS` — retention analysis
- `CONVERTEDOPPORTUNITYID` — conversion attribution

## Files

```
bi-dashboards/
├── README.md
├── specs/
│   ├── arr_dashboard_spec.md        # Metric definitions
│   ├── platform_adoption_spec.md
│   └── pipeline_health_spec.md
└── sql/
    ├── arr_base_query.sql
    ├── platform_usage_query.sql
    └── pipeline_coverage.sql
```
