# Project 06 — Black Box: Query Confidence Scorer + VQR Pusher

> **Stack**: Python · Snowflake Query History · GitHub API  
> **Status**: Production  
> **Threshold**: Score ≥ 90/100 → auto-push to VQR repo

## Overview

**Black Box** ingests a Snowflake query history CSV, scores each query against 6 quality signals, and automatically pushes queries that score ≥ 90/100 to a designated **Verified Query Repository (VQR)** on GitHub.

The goal: build a self-curating library of high-quality, production-safe SQL — no manual review needed for anything that clears the bar.

---

## Confidence Score — 6 Signals (100 pts total)

| # | Signal | Weight | Pass Condition |
|---|--------|--------|----------------|
| 1 | **No CROSS JOIN** | 20 pts | Query contains no `CROSS JOIN` |
| 2 | **Filters on large tables** | 20 pts | `WHERE` or `ON` present when a large table is referenced |
| 3 | **Fully qualified table names** | 20 pts | All tables use `db.schema.table` format |
| 4 | **Table names match prompt** | 20 pts | ≥ 40% of prompt keywords appear in the SQL |
| 5 | **No `SELECT *`** | 10 pts | Explicit column list — no wildcard projection |
| 6 | **Execution success** | 10 pts | Query ran without errors (`status = SUCCESS`) |

### Score interpretation

| Score | Status |
|-------|--------|
| **90–100** | ✅ VQR eligible — auto-pushed to GitHub repo |
| **70–89** | ⚠️ Near threshold — signal breakdown shown |
| **< 70** | ❌ Below threshold — fix required |

---

## How It Works

```
query_history.csv
      │
      ▼
┌─────────────────────┐
│  confidence_scorer  │  Runs 6 signal checks per query
│  .score_from_csv()  │  Returns QueryScore objects
└──────────┬──────────┘
           │
    score >= 90?
      │        │
     YES        NO
      │        │
      ▼        ▼
┌──────────┐  Skip / log
│  vqr_    │  to report
│  pusher  │
│ .push()  │  GitHub Contents API
└──────────┘
      │
      ▼
 vqr-queries/
   verified_queries/
     QH001_show_me_all_accounts_with_converted.sql
     QH002_count_accounts_by_industry.sql
     ...
```

---

## VQR File Format

Each pushed file includes a metadata header:

```sql
-- ============================================================
-- VQR VERIFIED QUERY
-- ============================================================
-- query_id   : QH001
-- score      : 100/100
-- scored_at  : 2024-11-15T10:30:00+00:00
-- prompt     : Show me all accounts with converted leads
-- status     : SUCCESS
-- signals    : no_cross_join=PASS, filters=PASS, fq_names=PASS,
--              table_match=PASS, no_select_star=PASS, execution=PASS
-- ============================================================

SELECT ACCOUNTID, ACCOUNT_NAME, ACCOUNT_TO_LEAD_CONVERSION
FROM BT_DEV.PCHOPRA.OBT_SALESFORCE
WHERE ACCOUNT_TO_LEAD_CONVERSION = TRUE
```

---

## Setup

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/analytics-portfolio.git
cd analytics-portfolio/projects/black-box-vqr
pip install -r requirements.txt

# 2. Set GitHub credentials (for VQR push)
export GITHUB_TOKEN=ghp_your_token_here
export VQR_REPO_OWNER=your_github_username
export VQR_REPO_NAME=vqr-queries          # your VQR repo name
export VQR_REPO_BRANCH=main
export VQR_FOLDER=verified_queries
```

---

## Usage

```bash
# Score queries and print summary
python main.py --input data/sample/query_history_sample.csv

# Dry run — see what would be pushed without writing to GitHub
python main.py --input data/sample/query_history_sample.csv --push --dry-run

# Live push to VQR GitHub repo
python main.py --input data/sample/query_history_sample.csv --push

# Export full score breakdown to JSON
python main.py --input data/sample/query_history_sample.csv --export results.json

# Score a single query from the CLI
python main.py \
  --query "SELECT ACCOUNTID, ACCOUNT_NAME FROM BT_DEV.PCHOPRA.OBT_SALESFORCE WHERE IS_WON=TRUE" \
  --prompt "Get all won accounts" \
  --status SUCCESS
```

### Sample output

```
────────────────────────────────────────────────────────────────────────────────
  BLACK BOX — Query Confidence Scorer
  Threshold: 90/100 for VQR eligibility
────────────────────────────────────────────────────────────────────────────────
  ID        SCORE    VQR  RECOMMENDATION
────────────────────────────────────────────────────────────────────────────────
  QH001       100    YES  ✅ VQR eligible — push to repo
  QH002       100    YES  ✅ VQR eligible — push to repo
  QH006       100    YES  ✅ VQR eligible — push to repo
  QH008        90    YES  ✅ VQR eligible — push to repo
  QH011       100    YES  ✅ VQR eligible — push to repo
  QH012       100    YES  ✅ VQR eligible — push to repo
  QH004        90    YES  ✅ VQR eligible — push to repo
  QH009        90    YES  ✅ VQR eligible — push to repo
  QH007        80     NO  ⚠️  Near threshold — fix: fully_qualified_names
  QH005        30     NO  ❌ Below threshold — fix: fully_qualified_names, execution_success
  QH003        10     NO  ❌ Below threshold — fix: filters, fq_names, table_match, no_select_star, execution
  QH010        50     NO  ❌ Below threshold — fix: no_cross_join, no_select_star
────────────────────────────────────────────────────────────────────────────────
  Total: 12 queries | VQR eligible: 8
```

---

## CSV Format

Your query history export needs these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `query_id` | ✅ | Unique identifier |
| `prompt` | ✅ | The natural language question that generated this query |
| `query_text` | ✅ | The SQL query |
| `execution_status` | ✅ | `SUCCESS` or `FAILED` |
| `start_time` | optional | For logging |
| `bytes_scanned` | optional | Ignored by scorer |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Files

```
black-box-vqr/
├── README.md
├── main.py                          # CLI entrypoint
├── requirements.txt
├── src/
│   ├── confidence_scorer.py         # 6-signal scorer logic
│   └── vqr_pusher.py               # GitHub API pusher
├── data/
│   └── sample/
│       └── query_history_sample.csv # 12 dummy queries for testing
└── tests/
    └── test_confidence_scorer.py    # pytest unit tests (30+ cases)
```
