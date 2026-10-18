"""
Clean Database Reset Script for Testing.

Safely purges all documents, claims, evidence links, trust scores,
evaluations, and chat sessions to establish a 100% clean testing state.
Preserves default demo organization and admin user so the UI/API server remain operational.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from sqlalchemy import text
from app.db.database import engine

TABLES_TO_TRUNCATE = [
    "agent_context_items",
    "agent_requests",
    "chat_messages",
    "chat_sessions",
    "claim_conflicts",
    "claim_evidence",
    "claim_trust_scores",
    "claim_validity",
    "claims",
    "decision_evaluations",
    "document_versions",
    "documents",
    "hitl_escalations",
    "human_reviews",
    "user_activity_logs",
    "webhook_dispatch_logs",
    "webhook_subscriptions",
]


async def reset_database(full_wipe: bool = False):
    print("=" * 60)
    print("Context Layer AI - Clean Database Reset")
    print("=" * 60)

    async with engine.begin() as conn:
        print("\n1. Truncating document, claim, and evaluation tables...")
        for table in TABLES_TO_TRUNCATE:
            try:
                await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE;'))
                print(f"   [OK] Purged {table}")
            except Exception as e:
                print(f"   - Skipped {table}: {e}")

        if full_wipe:
            print("\n2. Full wipe requested: clearing data sources, non-demo orgs and users...")
            try:
                await conn.execute(text("TRUNCATE TABLE data_sources CASCADE;"))
                print("   [OK] Purged data_sources")
                await conn.execute(text("DELETE FROM users WHERE id != '22222222-2222-2222-2222-222222222222';"))
                print("   [OK] Cleaned extra users (preserved admin sarah.chen@demo.local)")
                await conn.execute(text("DELETE FROM organizations WHERE id != '11111111-1111-1111-1111-111111111111';"))
                print("   [OK] Cleaned extra organizations (preserved demo org)")
            except Exception as e:
                print(f"   - Warning during full wipe: {e}")

    # Post-wipe verification
    print("\n3. Post-wipe verification:")
    async with engine.connect() as conn:
        doc_cnt = (await conn.execute(text("SELECT count(*) FROM documents;"))).scalar()
        claim_cnt = (await conn.execute(text("SELECT count(*) FROM claims;"))).scalar()
        eval_cnt = (await conn.execute(text("SELECT count(*) FROM decision_evaluations;"))).scalar()
        print(f"   Documents in DB: {doc_cnt}")
        print(f"   Claims in DB:    {claim_cnt}")
        print(f"   Evaluations:     {eval_cnt}")

    if doc_cnt == 0 and claim_cnt == 0:
        print("\nSUCCESS: Database successfully reset to pristine state!")
    else:
        print(f"\nWARNING: Some records remain (docs={doc_cnt}, claims={claim_cnt})")


def main():
    parser = argparse.ArgumentParser(description="Reset Context Layer AI database for clean testing")
    parser.add_argument("--full", action="store_true", help="Also wipe non-demo users, orgs, and data sources")
    parser.add_argument("--yes", action="store_true", help="Bypass interactive confirmation")

    args = parser.parse_args()

    if not args.yes:
        print("This will PERMANENTLY ERASE all documents, claims, and evaluations in the database.")
        res = input("Are you sure you want to proceed? [y/N]: ").strip().lower()
        if res not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    asyncio.run(reset_database(full_wipe=args.full))


if __name__ == "__main__":
    main()