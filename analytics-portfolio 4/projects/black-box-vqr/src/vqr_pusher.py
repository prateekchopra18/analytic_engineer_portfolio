"""
vqr_pusher.py
-------------
Takes VQR-eligible queries (score >= 90) and pushes them to a GitHub repo
as individual .sql files with a YAML front-matter header containing metadata.

Each file is pushed via the GitHub Contents API (no git CLI needed).

File naming convention:
    {query_id}_{slug_from_prompt}.sql

Front-matter example (inside SQL comment block):
    -- query_id:    QH001
    -- prompt:      Show me all accounts with converted leads
    -- score:       100
    -- scored_at:   2024-11-15T10:30:00
    -- signals:     no_cross_join=PASS, filters=PASS, fq_names=PASS, ...
"""

import os
import re
import json
import base64
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from confidence_scorer import QueryScore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config (set via environment variables)
# ---------------------------------------------------------------------------

GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
VQR_REPO_OWNER  = os.environ.get("VQR_REPO_OWNER", "")      # e.g. "prateekchopra"
VQR_REPO_NAME   = os.environ.get("VQR_REPO_NAME",  "vqr-queries")
VQR_REPO_BRANCH = os.environ.get("VQR_REPO_BRANCH", "main")
VQR_FOLDER      = os.environ.get("VQR_FOLDER", "verified_queries")  # folder in repo

GITHUB_API_BASE = "https://api.github.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str, max_len: int = 40) -> str:
    """Convert prompt to a safe filename slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:max_len]


def _build_sql_file(query: QueryScore, scored_at: str) -> str:
    """Build the .sql file content with metadata header."""
    signal_summary = ", ".join(
        f"{s.name}={'PASS' if s.passed else 'FAIL'}"
        for s in query.signals
    )

    header = f"""-- ============================================================
-- VQR VERIFIED QUERY
-- ============================================================
-- query_id   : {query.query_id}
-- score      : {query.total_score}/100
-- scored_at  : {scored_at}
-- prompt     : {query.prompt}
-- status     : {query.execution_status}
-- signals    : {signal_summary}
-- ============================================================

"""
    return header + query.query_text.strip() + "\n"


def _get_file_sha(
    owner: str,
    repo: str,
    path: str,
    token: str,
    branch: str,
) -> Optional[str]:
    """Return the SHA of an existing file, or None if it doesn't exist."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(
        url,
        headers={"Authorization": f"token {token}"},
        params={"ref": branch},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def push_to_github(query: QueryScore, dry_run: bool = False) -> dict:
    """
    Push a single VQR-eligible query to the GitHub repo.

    Returns a dict with:
        - query_id
        - filename
        - github_url (if successful)
        - status: "pushed" | "updated" | "dry_run" | "error"
        - message
    """
    if not query.vqr_eligible:
        return {
            "query_id": query.query_id,
            "status":   "skipped",
            "message":  f"Score {query.total_score} below VQR threshold",
        }

    scored_at = datetime.now(timezone.utc).isoformat()
    slug      = _slugify(query.prompt)
    filename  = f"{query.query_id}_{slug}.sql"
    repo_path = f"{VQR_FOLDER}/{filename}"
    content   = _build_sql_file(query, scored_at)
    encoded   = base64.b64encode(content.encode()).decode()

    if dry_run:
        return {
            "query_id": query.query_id,
            "filename": filename,
            "repo_path": repo_path,
            "status":   "dry_run",
            "message":  "Dry run — file not pushed",
            "content_preview": content[:300] + "...",
        }

    if not GITHUB_TOKEN or not VQR_REPO_OWNER:
        return {
            "query_id": query.query_id,
            "status":   "error",
            "message":  "GITHUB_TOKEN or VQR_REPO_OWNER env vars not set",
        }

    # Check if file already exists (update vs create)
    existing_sha = _get_file_sha(
        VQR_REPO_OWNER, VQR_REPO_NAME, repo_path, GITHUB_TOKEN, VQR_REPO_BRANCH
    )
    action = "updated" if existing_sha else "pushed"

    payload = {
        "message": f"vqr: {'update' if existing_sha else 'add'} {filename} (score={query.total_score})",
        "content": encoded,
        "branch":  VQR_REPO_BRANCH,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    url  = f"{GITHUB_API_BASE}/repos/{VQR_REPO_OWNER}/{VQR_REPO_NAME}/contents/{repo_path}"
    resp = requests.put(
        url,
        headers={
            "Authorization": f"token {token}",
            "Content-Type":  "application/json",
        },
        json=payload,
        timeout=15,
    )

    if resp.status_code in (200, 201):
        github_url = resp.json().get("content", {}).get("html_url", "")
        logger.info("VQR push success: %s → %s", filename, github_url)
        return {
            "query_id":   query.query_id,
            "filename":   filename,
            "github_url": github_url,
            "status":     action,
            "message":    f"Score {query.total_score}/100 — {action} in {VQR_REPO_NAME}",
        }
    else:
        logger.error("GitHub push failed: %s %s", resp.status_code, resp.text)
        return {
            "query_id": query.query_id,
            "status":   "error",
            "message":  f"GitHub API error {resp.status_code}: {resp.text[:200]}",
        }


def push_batch(queries: list[QueryScore], dry_run: bool = False) -> list[dict]:
    """Push all VQR-eligible queries from a batch."""
    results = []
    for q in queries:
        result = push_to_github(q, dry_run=dry_run)
        results.append(result)
        status = result["status"]
        logger.info("[%s] %s → %s", q.query_id, q.total_score, status)
    return results
