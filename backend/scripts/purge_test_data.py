import asyncio
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def purge():
    async with AsyncSessionLocal() as session:
        print("Starting comprehensive database purge...")

        statements = [
            "DELETE FROM agent_context_items;",
            "DELETE FROM agent_requests;",
            "DELETE FROM decision_evaluations;",
            "DELETE FROM human_reviews;",
            "DELETE FROM hitl_escalations;",
            "DELETE FROM claim_conflicts;",
            "DELETE FROM claim_trust_scores;",
            "DELETE FROM claim_evidence;",
            "DELETE FROM claim_validity;",
            "DELETE FROM claims;",
            "DELETE FROM document_versions;",
            "DELETE FROM documents;",
            "DELETE FROM data_sources WHERE id != '44444444-4444-4444-4444-444444444444';",
            "DELETE FROM user_activity_logs;"
        ]

        for stmt in statements:
            try:
                result = await session.execute(text(stmt))
                print(f"Success: {stmt} -> rows affected: {result.rowcount}")
            except Exception as e:
                print(f"Skipping or error on '{stmt}': {e}")
                await session.rollback()

        await session.commit()
        print("\nAll changes committed.")

        print("\n--- Current Table Counts ---")
        tables_to_check = [
            "documents",
            "document_versions",
            "claims",
            "claim_conflicts",
            "claim_evidence",
            "claim_trust_scores",
            "claim_validity",
            "data_sources",
            "decision_evaluations",
            "agent_context_items"
        ]
        for tbl in tables_to_check:
            try:
                res = await session.execute(text(f"SELECT count(*) FROM {tbl};"))
                print(f"{tbl}: {res.scalar()}")
            except Exception as e:
                print(f"{tbl}: error checking count ({e})")

if __name__ == "__main__":
    asyncio.run(purge())
