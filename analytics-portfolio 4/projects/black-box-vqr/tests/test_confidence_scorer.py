"""
test_confidence_scorer.py
--------------------------
Unit tests for all 6 signal checkers + the composite scorer.
Run with: pytest tests/
"""

import pytest
from src.confidence_scorer import (
    check_no_cross_join,
    check_filters_on_large_tables,
    check_fully_qualified_names,
    check_table_names_match_prompt,
    check_no_select_star,
    check_execution_success,
    score_query,
    VQR_THRESHOLD,
)


# ── Signal 1: No CROSS JOIN ────────────────────────────────────────────────

class TestNoCrossJoin:
    def test_pass_inner_join(self):
        sql = "SELECT a.id FROM DB.SCH.A a JOIN DB.SCH.B b ON a.id = b.id"
        r = check_no_cross_join(sql)
        assert r.passed is True
        assert r.score == r.weight

    def test_fail_cross_join(self):
        sql = "SELECT * FROM DB.SCH.A CROSS JOIN DB.SCH.B"
        r = check_no_cross_join(sql)
        assert r.passed is False
        assert r.score == 0

    def test_fail_cross_join_lowercase(self):
        sql = "select * from a cross join b"
        r = check_no_cross_join(sql)
        assert r.passed is False

    def test_pass_no_join(self):
        sql = "SELECT COUNT(*) FROM DB.SCH.TABLE WHERE ID = 1"
        r = check_no_cross_join(sql)
        assert r.passed is True


# ── Signal 2: Filters on large tables ─────────────────────────────────────

class TestFiltersOnLargeTables:
    def test_pass_small_table(self):
        sql = "SELECT * FROM SMALL_LOOKUP_TABLE"
        r = check_filters_on_large_tables(sql)
        assert r.passed is True

    def test_fail_large_table_no_where(self):
        sql = "SELECT ACCOUNTID FROM BT_DEV.PCHOPRA.OBT_SALESFORCE"
        r = check_filters_on_large_tables(sql)
        assert r.passed is False
        assert r.score == 0

    def test_pass_large_table_with_where(self):
        sql = "SELECT ACCOUNTID FROM BT_DEV.PCHOPRA.OBT_SALESFORCE WHERE IS_WON = TRUE"
        r = check_filters_on_large_tables(sql)
        assert r.passed is True

    def test_pass_large_table_with_join_on(self):
        sql = ("SELECT a.ID FROM BT_DEV.PCHOPRA.OBT_SALESFORCE a "
               "JOIN DB.SCH.OTHER b ON a.ID = b.ID")
        r = check_filters_on_large_tables(sql)
        assert r.passed is True


# ── Signal 3: Fully qualified names ───────────────────────────────────────

class TestFullyQualifiedNames:
    def test_pass_three_part(self):
        sql = "SELECT ID FROM BT_DEV.PCHOPRA.OBT_SALESFORCE WHERE X = 1"
        r = check_fully_qualified_names(sql)
        assert r.passed is True

    def test_fail_one_part(self):
        sql = "SELECT ID FROM OBT_SALESFORCE WHERE X = 1"
        r = check_fully_qualified_names(sql)
        assert r.passed is False
        assert "OBT_SALESFORCE" in r.detail

    def test_fail_two_part(self):
        sql = "SELECT ID FROM PCHOPRA.OBT_SALESFORCE WHERE X = 1"
        r = check_fully_qualified_names(sql)
        assert r.passed is False

    def test_pass_multiple_tables_all_qualified(self):
        sql = ("SELECT a.ID FROM DB.SCH.TABLE_A a "
               "JOIN DB.SCH.TABLE_B b ON a.ID = b.ID")
        r = check_fully_qualified_names(sql)
        assert r.passed is True

    def test_fail_mixed_qualification(self):
        sql = ("SELECT a.ID FROM DB.SCH.TABLE_A a "
               "JOIN TABLE_B b ON a.ID = b.ID")
        r = check_fully_qualified_names(sql)
        assert r.passed is False


# ── Signal 4: Table names match prompt ────────────────────────────────────

class TestTableNamesMatchPrompt:
    def test_pass_strong_match(self):
        sql    = "SELECT ACCOUNTID, CONTRACT_NAME FROM BT_DEV.PCHOPRA.OBT_SALESFORCE WHERE CONTRACT_STATUS = 'Activated'"
        prompt = "Show me all active contracts with account names"
        r = check_table_names_match_prompt(sql, prompt)
        assert r.passed is True

    def test_fail_no_match(self):
        sql    = "SELECT ID FROM DB.SCH.UNRELATED_TABLE WHERE X = 1"
        prompt = "Show me all converted leads from Salesforce accounts"
        r = check_table_names_match_prompt(sql, prompt)
        assert r.passed is False

    def test_pass_partial_match(self):
        # ACCOUNTS→ACCOUNT_NAME, LEADS→LEADID both match; 2/3 keywords = 67% > 40%
        sql    = "SELECT ACCOUNT_NAME FROM DB.SCH.OBT_SALESFORCE WHERE LEADID IS NOT NULL"
        prompt = "Get accounts with leads converted"
        r = check_table_names_match_prompt(sql, prompt)
        assert r.passed is True


# ── Signal 5: No SELECT * ─────────────────────────────────────────────────

class TestNoSelectStar:
    def test_pass_explicit_columns(self):
        sql = "SELECT ACCOUNTID, ACCOUNT_NAME FROM DB.SCH.TABLE WHERE X=1"
        r = check_no_select_star(sql)
        assert r.passed is True

    def test_fail_select_star(self):
        sql = "SELECT * FROM DB.SCH.TABLE"
        r = check_no_select_star(sql)
        assert r.passed is False
        assert r.score == 0

    def test_fail_aliased_star(self):
        sql = "SELECT t.* FROM DB.SCH.TABLE t"
        r = check_no_select_star(sql)
        assert r.passed is False

    def test_pass_count_star(self):
        # COUNT(*) is fine — * is not a projection
        sql = "SELECT COUNT(*) FROM DB.SCH.TABLE WHERE X=1"
        r = check_no_select_star(sql)
        assert r.passed is True


# ── Signal 6: Execution success ───────────────────────────────────────────

class TestExecutionSuccess:
    def test_pass_success(self):
        r = check_execution_success("SUCCESS")
        assert r.passed is True

    def test_fail_failed(self):
        r = check_execution_success("FAILED")
        assert r.passed is False
        assert r.score == 0

    def test_case_insensitive(self):
        r = check_execution_success("success")
        assert r.passed is True

    def test_fail_unknown(self):
        r = check_execution_success("UNKNOWN")
        assert r.passed is False


# ── Composite scorer ──────────────────────────────────────────────────────

class TestCompositeScorer:
    def test_perfect_score(self):
        sql = (
            "SELECT ACCOUNTID, ACCOUNT_NAME, ACCOUNT_TO_LEAD_CONVERSION "
            "FROM BT_DEV.PCHOPRA.OBT_SALESFORCE "
            "WHERE ACCOUNT_TO_LEAD_CONVERSION = TRUE"
        )
        result = score_query("T001", "Show accounts with converted leads", sql, "SUCCESS")
        assert result.total_score == 100
        assert result.vqr_eligible is True

    def test_failed_query_loses_10pts(self):
        sql = (
            "SELECT ACCOUNTID FROM BT_DEV.PCHOPRA.OBT_SALESFORCE "
            "WHERE IS_WON = TRUE"
        )
        result = score_query("T002", "Get won accounts", sql, "FAILED")
        assert result.total_score == 90
        assert result.vqr_eligible is True   # still >= 90

    def test_select_star_loses_10pts(self):
        # SELECT * costs 10pts; use a prompt with enough keywords to pass signal 4
        sql = (
            "SELECT * FROM BT_DEV.PCHOPRA.OBT_SALESFORCE "
            "WHERE IS_WON = TRUE AND CLOSE_DATE >= '2024-01-01'"
        )
        result = score_query("T003", "Get all won opportunities closed in 2024", sql, "SUCCESS")
        assert result.total_score == 90   # loses 10 for SELECT *

    def test_cross_join_fails_vqr(self):
        sql = "SELECT * FROM BT_DEV.PCHOPRA.OBT_SALESFORCE CROSS JOIN DB.SCH.OTHER"
        result = score_query("T004", "Get all data", sql, "SUCCESS")
        assert result.vqr_eligible is False

    def test_vqr_threshold(self):
        # A query that scores exactly at threshold should be eligible
        assert VQR_THRESHOLD == 90
