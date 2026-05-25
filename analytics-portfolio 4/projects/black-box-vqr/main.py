"""
main.py
-------
CLI entrypoint for the Black Box Query Confidence Scorer + VQR Pusher.

Usage:
    # Score queries and show summary
    python main.py --input data/sample/query_history_sample.csv

    # Score + push eligible queries to GitHub (dry run first)
    python main.py --input data/sample/query_history_sample.csv --push --dry-run

    # Score + push for real
    python main.py --input data/sample/query_history_sample.csv --push

    # Export full results to JSON
    python main.py --input data/sample/query_history_sample.csv --export results.json

    # Score a single query inline
    python main.py --query "SELECT ACCOUNTID FROM BT_DEV.PCHOPRA.OBT_SALESFORCE WHERE IS_WON=TRUE" \
                   --prompt "Get all won accounts" \
                   --status SUCCESS
"""

import argparse
import json
import logging
import sys

from confidence_scorer import score_query, score_from_csv, get_vqr_eligible, print_summary
from vqr_pusher import push_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(
        description="Black Box — Snowflake Query Confidence Scorer & VQR Pusher"
    )

    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--input",  help="Path to query history CSV file")
    source.add_argument("--query",  help="Single SQL query string to score")

    p.add_argument("--prompt",  default="",       help="Prompt for single --query mode")
    p.add_argument("--status",  default="SUCCESS",help="Execution status for --query mode")
    p.add_argument("--push",    action="store_true", help="Push VQR-eligible queries to GitHub")
    p.add_argument("--dry-run", action="store_true", help="Simulate push without writing to GitHub")
    p.add_argument("--export",  help="Export full results to a JSON file")
    p.add_argument("--threshold", type=int, default=90,
                   help="VQR eligibility threshold (default: 90)")

    return p.parse_args()


def main():
    args = parse_args()

    # ── Score ─────────────────────────────────────────────────────────────
    if args.input:
        logger.info("Loading query history from: %s", args.input)
        results = score_from_csv(args.input)
    else:
        results = [score_query(
            query_id         = "CLI001",
            prompt           = args.prompt,
            query_text       = args.query,
            execution_status = args.status,
        )]

    print_summary(results)

    # ── Export JSON ────────────────────────────────────────────────────────
    if args.export:
        with open(args.export, "w") as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        logger.info("Results exported to: %s", args.export)

    # ── Push to VQR GitHub repo ────────────────────────────────────────────
    if args.push:
        eligible = get_vqr_eligible(results)
        logger.info(
            "%d/%d queries VQR eligible (score >= %d)",
            len(eligible), len(results), args.threshold
        )

        if not eligible:
            logger.warning("No queries met the threshold — nothing to push.")
            sys.exit(0)

        push_results = push_batch(eligible, dry_run=args.dry_run)

        print(f"\n{'─'*60}")
        print(f"  VQR PUSH RESULTS {'(DRY RUN)' if args.dry_run else ''}")
        print(f"{'─'*60}")
        for r in push_results:
            icon = {"pushed": "✅", "updated": "🔄", "dry_run": "🔵",
                    "skipped": "⏭", "error": "❌"}.get(r["status"], "?")
            print(f"  {icon}  {r.get('query_id','?'):8}  {r['status']:10}  {r['message']}")
            if r.get("github_url"):
                print(f"         → {r['github_url']}")
        print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
