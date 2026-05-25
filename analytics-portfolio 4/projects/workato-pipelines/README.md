# Project 02 — Workato Usage Pipeline

> **Stack**: Workato · Snowflake · Python  
> **Status**: Production  
> **Tables**: `DATA_GENIE.WORKATO_USAGE.*`

## Overview

End-to-end ETL pipeline that ingests Workato platform usage data (recipes, connections, active users) into Snowflake for BI consumption. Implements incremental loading patterns with full error handling and audit logging.

## Pipeline Architecture

```
Workato Platform API
        │
        ▼
┌───────────────────┐
│  Trigger (Cron)   │  Daily at 02:00 UTC
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│  Run Custom SQL   │  Fetch last watermark
│  (Snowflake)      │  from control table
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│   FOR EACH Batch  │  Paginate through API
│   (Workato)       │  in chunks of 100
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│  MONITOR block    │  Error isolation per row
│  + DO NOT RETRY   │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│  Replicate to     │  Batch upsert to
│  Snowflake        │  AGGREGATED_* tables
└───────────────────┘
```

## Target Tables

### `AGGREGATED_RECIPES_OVER_TIME_COMB`
Tracks active recipe counts per workspace per day.

| Column | Type | Description |
|--------|------|-------------|
| WORKSPACE_ID | VARCHAR | Workato workspace identifier |
| DATE | DATE | Snapshot date |
| ACTIVE_RECIPES | NUMBER | Count of active recipes |
| TOTAL_RECIPES | NUMBER | Total recipe count |
| UPDATED_AT | TIMESTAMP | ETL load timestamp |

### `AGGREGATED_CONNECTIONS_OVER_TIME_COMB`
Tracks active connection counts per workspace per day.

| Column | Type | Description |
|--------|------|-------------|
| WORKSPACE_ID | VARCHAR | Workato workspace identifier |
| DATE | DATE | Snapshot date |
| ACTIVE_CONNECTIONS | NUMBER | Active connection count |
| TOTAL_CONNECTIONS | NUMBER | Total connections |
| UPDATED_AT | TIMESTAMP | ETL load timestamp |

## Error Handling Pattern

```
FOR EACH item in batch
  └── MONITOR for error
        └── API call (Freshdesk / Workato)
        └── ERROR FOUND?
              ├── Yes → DO NOT RETRY → Log to Job report
              └── No  → Add to list → Replicate → continue
```

Key decisions:
- `MONITOR` wraps **only** the API call, not the Replicate step
- `DO NOT RETRY` prevents job failure cascade on 404s
- Each ticket/record is isolated — one failure doesn't poison the batch
- All errors written to Job Report for audit trail

## Files

```
workato-pipelines/
├── README.md
├── recipes/
│   ├── usage_pipeline_design.md     # Recipe flow documentation
│   └── error_handling_patterns.md  # MONITOR block best practices
└── sql/
    ├── watermark_query.sql          # Incremental load control
    └── usage_aggregation.sql        # Post-load aggregations
```
