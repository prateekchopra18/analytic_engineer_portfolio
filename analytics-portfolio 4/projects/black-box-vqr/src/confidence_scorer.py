"""
confidence_scorer.py
--------------------
Scores a SQL query against a natural language prompt using 6 signals.
Returns a score 0–100 and a per-signal breakdown.

Signals (weighted):
    1. No CROSS JOIN present                    (20 pts)
    2. WHERE / filter present on large tables   (20 pts)
    3. Fully qualified table names (db.schema.table) (20 pts)
    4. Table names match prompt intent          (20 pts)
    5. No SELECT *                              (10 pts)
    6. Query executed successfully (no errors)  (10 pts)

Total: 100 pts. Queries scoring >= 90 are eligible for VQR repo push.
"""

import re
import csv
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VQR_THRESHOLD = 90          # minimum score to push to VQR repo

# Known large tables that MUST have a WHERE clause filter
LARGE_TABLES = {
    "OBT_SALESFORCE",
    "AGGREGATED_RECIPES_OVER_TIME_COMB",
    "AGGREGATED_CONNECTIONS_OVER_TIME_COMB",
    "QUERY_HISTORY",
    "ACCESS_HISTORY",
}

# Signal weights (must sum to 100)
WEIGHTS = {
    "no_cross_join":            20,
    "filters_on_large_tables":  20,
    "fully_qualified_names":    20,
    "table_names_match_prompt": 20,
    "no_select_star":           10,
    "execution_success":        10,
}

assert sum(WEIGHTS.values()) == 100, "Signal weights must sum to 100"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    name: str
    passed: bool
    weight: int
    score: int          # weight if passed, 0 if failed
    detail: str         # human-readable explanation


@dataclass
class QueryScore:
    query_id: str
    prompt: str
    query_text: str
    execution_status: str
    total_score: int
    vqr_eligible: bool
    signals: list[SignalResult] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["signals"] = [asdict(s) for s in self.signals]
        return d


# ---------------------------------------------------------------------------
# Signal checkers
# ---------------------------------------------------------------------------

def _normalise(sql: str) -> str:
    """Uppercase, collapse whitespace."""
    return re.sub(r"\s+", " ", sql.upper().strip())


def check_no_cross_join(sql: str) -> SignalResult:
    """Fail if CROSS JOIN is present anywhere in the query."""
    norm = _normalise(sql)
    found = bool(re.search(r"\bCROSS\s+JOIN\b", norm))
    return SignalResult(
        name="no_cross_join",
        passed=not found,
        weight=WEIGHTS["no_cross_join"],
        score=0 if found else WEIGHTS["no_cross_join"],
        detail="CROSS JOIN detected — risk of row explosion" if found
               else "No CROSS JOIN found",
    )


def check_filters_on_large_tables(sql: str) -> SignalResult:
    """
    Pass if:
      - No large table referenced, OR
      - At least one WHERE / JOIN ... ON condition is present when a large
        table IS referenced.
    """
    norm = _normalise(sql)
    tables_hit = [t for t in LARGE_TABLES if t in norm]

    if not tables_hit:
        return SignalResult(
            name="filters_on_large_tables",
            passed=True,
            weight=WEIGHTS["filters_on_large_tables"],
            score=WEIGHTS["filters_on_large_tables"],
            detail="No known large tables referenced",
        )

    has_where = bool(re.search(r"\bWHERE\b", norm))
    has_join_on = bool(re.search(r"\bON\b", norm))
    passed = has_where or has_join_on

    return SignalResult(
        name="filters_on_large_tables",
        passed=passed,
        weight=WEIGHTS["filters_on_large_tables"],
        score=WEIGHTS["filters_on_large_tables"] if passed else 0,
        detail=f"Large table(s) {tables_hit} "
               + ("have WHERE/ON filter" if passed
                  else "referenced with NO WHERE or JOIN condition — full scan risk"),
    )


def check_fully_qualified_names(sql: str) -> SignalResult:
    """
    Extract all table references and check that each uses db.schema.table format.
    We look for FROM / JOIN tokens followed by an identifier.
    """
    norm = _normalise(sql)
    # Match tokens after FROM / JOIN (skip sub-queries starting with '(')
    pattern = r"(?:FROM|JOIN)\s+([A-Z0-9_$.\"]+)"
    refs = re.findall(pattern, norm)
    # Filter out SQL keywords that can follow FROM/JOIN
    keywords = {"WHERE", "ON", "SET", "SELECT", "WITH", "LATERAL", "UNNEST"}
    refs = [r for r in refs if r not in keywords and not r.startswith("(")]

    if not refs:
        return SignalResult(
            name="fully_qualified_names",
            passed=False,
            weight=WEIGHTS["fully_qualified_names"],
            score=0,
            detail="No table references found — could not evaluate qualification",
        )

    # A fully qualified name has at least 2 dots: db.schema.table
    unqualified = [r for r in refs if r.count(".") < 2]
    passed = len(unqualified) == 0

    return SignalResult(
        name="fully_qualified_names",
        passed=passed,
        weight=WEIGHTS["fully_qualified_names"],
        score=WEIGHTS["fully_qualified_names"] if passed else 0,
        detail="All table refs fully qualified (db.schema.table)" if passed
               else f"Unqualified table refs: {unqualified}",
    )


def check_table_names_match_prompt(sql: str, prompt: str) -> SignalResult:
    """
    Tokenise the prompt into meaningful keywords and check that at least
    one significant token appears in the SQL (as a table/column name).
    Uses prefix matching (first 5 chars) to handle plurals and snake_case.
    e.g. 'contracts' matches 'CONTRACT_NAME', 'CONTRACT_STATUS'
    """
    STOP = {
        "show", "get", "find", "list", "give", "top", "select",
        "with", "me", "the", "a", "an", "for", "and", "or", "of",
        "in", "on", "by", "to", "is", "are", "that", "which",
        "how", "count", "sum", "total", "all", "from",
        "where", "into", "each", "per", "about", "many", "have",
    }
    norm_sql    = _normalise(sql)
    norm_prompt = prompt.upper()

    tokens = re.findall(r"[A-Z]+", norm_prompt)
    keywords = [t for t in tokens if t not in STOP and len(t) > 3]

    if not keywords:
        return SignalResult(
            name="table_names_match_prompt",
            passed=False,
            weight=WEIGHTS["table_names_match_prompt"],
            score=0,
            detail="Could not extract meaningful keywords from prompt",
        )

    # Prefix match: keyword prefix appears at the START of any SQL token
    # e.g. "LEADS" (prefix "LEAD") matches "LEADID" which starts with "LEAD"
    sql_tokens = re.findall(r"[A-Z]+", norm_sql)

    def _matches(keyword: str) -> bool:
        prefix = keyword[:4]   # 4-char prefix handles plurals well
        return any(t.startswith(prefix) for t in sql_tokens)

    matched   = [k for k in keywords if _matches(k)]
    match_pct = len(matched) / len(keywords)
    passed    = match_pct >= 0.4      # at least 40% of prompt keywords appear in SQL

    return SignalResult(
        name="table_names_match_prompt",
        passed=passed,
        weight=WEIGHTS["table_names_match_prompt"],
        score=WEIGHTS["table_names_match_prompt"] if passed else 0,
        detail=f"{len(matched)}/{len(keywords)} prompt keywords found in SQL "
               f"({match_pct:.0%}) — {'PASS' if passed else 'FAIL (< 40%)'}. "
               f"Matched: {matched}",
    )


def check_no_select_star(sql: str) -> SignalResult:
    """Fail if SELECT * is present (lazy projection — pulls all columns)."""
    norm   = _normalise(sql)
    # SELECT * or SELECT a.* or SELECT t.*
    found  = bool(re.search(r"SELECT\s+\*|SELECT\s+\w+\.\*", norm))
    return SignalResult(
        name="no_select_star",
        passed=not found,
        weight=WEIGHTS["no_select_star"],
        score=0 if found else WEIGHTS["no_select_star"],
        detail="SELECT * detected — explicit column list preferred" if found
               else "No SELECT * — explicit columns used",
    )


def check_execution_success(execution_status: str) -> SignalResult:
    """Pass only if the query actually ran without errors."""
    passed = execution_status.upper() == "SUCCESS"
    return SignalResult(
        name="execution_success",
        passed=passed,
        weight=WEIGHTS["execution_success"],
        score=WEIGHTS["execution_success"] if passed else 0,
        detail=f"Execution status: {execution_status}",
    )


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

def score_query(
    query_id: str,
    prompt: str,
    query_text: str,
    execution_status: str,
) -> QueryScore:
    """Run all 6 signal checks and return a QueryScore."""

    signals = [
        check_no_cross_join(query_text),
        check_filters_on_large_tables(query_text),
        check_fully_qualified_names(query_text),
        check_table_names_match_prompt(query_text, prompt),
        check_no_select_star(query_text),
        check_execution_success(execution_status),
    ]

    total = sum(s.score for s in signals)
    eligible = total >= VQR_THRESHOLD

    failed_signals = [s.name for s in signals if not s.passed]
    if eligible:
        recommendation = "✅ VQR eligible — push to repo"
    elif total >= 70:
        recommendation = f"⚠️  Near threshold — fix: {', '.join(failed_signals)}"
    else:
        recommendation = f"❌ Below threshold — fix: {', '.join(failed_signals)}"

    return QueryScore(
        query_id=query_id,
        prompt=prompt,
        query_text=query_text,
        execution_status=execution_status,
        total_score=total,
        vqr_eligible=eligible,
        signals=signals,
        recommendation=recommendation,
    )


# ---------------------------------------------------------------------------
# Batch scorer from CSV
# ---------------------------------------------------------------------------

def score_from_csv(csv_path: str) -> list[QueryScore]:
    """
    Load a query history CSV and score every row.

    Expected columns: query_id, prompt, query_text, execution_status
    (extra columns like start_time, bytes_scanned etc. are ignored)
    """
    results = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = score_query(
                query_id        = row["query_id"],
                prompt          = row.get("prompt", ""),
                query_text      = row["query_text"],
                execution_status= row.get("execution_status", "UNKNOWN"),
            )
            results.append(result)
    return results


def get_vqr_eligible(results: list[QueryScore]) -> list[QueryScore]:
    """Filter to only VQR-eligible queries (score >= 90)."""
    return [r for r in results if r.vqr_eligible]


def print_summary(results: list[QueryScore]) -> None:
    """Print a formatted summary table to stdout."""
    print(f"\n{'─'*80}")
    print(f"  BLACK BOX — Query Confidence Scorer")
    print(f"  Threshold: {VQR_THRESHOLD}/100 for VQR eligibility")
    print(f"{'─'*80}")
    print(f"  {'ID':<8} {'SCORE':>5}  {'VQR':>5}  RECOMMENDATION")
    print(f"{'─'*80}")
    for r in sorted(results, key=lambda x: x.total_score, reverse=True):
        vqr = "YES" if r.vqr_eligible else "NO"
        print(f"  {r.query_id:<8} {r.total_score:>5}  {vqr:>5}  {r.recommendation}")
    print(f"{'─'*80}")
    eligible_count = sum(1 for r in results if r.vqr_eligible)
    print(f"  Total: {len(results)} queries | VQR eligible: {eligible_count}\n")
