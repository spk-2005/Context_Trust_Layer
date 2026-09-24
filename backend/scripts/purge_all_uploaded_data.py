import asyncio
import sys
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal


async def purge_all_data():
    async with AsyncSessionLocal() as session:
        print("Purging all uploaded documents, claims, conflicts, and sessions...")

        # 1. Delete all ingested and dependent data in cascade order
        await session.execute(text("DELETE FROM human_reviews;"))
        await session.execute(text("DELETE FROM agent_context_items;"))
        await session.execute(text("DELETE FROM agent_requests;"))
        await session.execute(text("DELETE FROM chat_messages;"))
        await session.execute(text("DELETE FROM chat_sessions;"))
        await session.execute(text("DELETE FROM decision_evaluations;"))
        await session.execute(text("DELETE FROM claim_conflicts;"))
        await session.execute(text("DELETE FROM claim_trust_scores;"))
        await session.execute(text("DELETE FROM claim_validity;"))
        await session.execute(text("DELETE FROM claim_evidence;"))
        await session.execute(text("DELETE FROM claims;"))
        await session.execute(text("DELETE FROM document_versions;"))
        await session.execute(text("DELETE FROM documents;"))
        await session.execute(text("DELETE FROM data_sources;"))
        await session.execute(text("DELETE FROM user_activity_logs;"))
        await session.execute(text("DELETE FROM users;"))
        await session.execute(text("DELETE FROM agents;"))
        await session.execute(text("DELETE FROM organizations;"))

        # 2. Seed pristine canonical baseline environment
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        user_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
        source_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

        # Insert Default Organization
        await session.execute(
            text("""
            INSERT INTO organizations (id, name, slug, status)
            VALUES (:id, 'Context Trust Corp', 'demo', 'active')
            ON CONFLICT (id) DO UPDATE SET name = 'Context Trust Corp', slug = 'demo';
            """),
            {"id": org_id},
        )

        # Insert Default User
        await session.execute(
            text("""
            INSERT INTO users (id, organization_id, name, email, role, status)
            VALUES (:id, :org_id, 'Diana Vance', 'diana.vance@demo.local', 'reviewer', 'active')
            ON CONFLICT (id) DO UPDATE SET name = 'Diana Vance', email = 'diana.vance@demo.local';
            """),
            {"id": user_id, "org_id": org_id},
        )

        # Insert Default Agent
        await session.execute(
            text("""
            INSERT INTO agents (id, organization_id, name, description, agent_type, model_provider, model_name, status)
            VALUES (:id, :org_id, 'Autonomous AI Copilot', 'Enterprise contextual copilot for policy verification.', 'claude_mcp_client', 'mock', 'gpt-4o', 'active')
            ON CONFLICT (id) DO NOTHING;
            """),
            {"id": agent_id, "org_id": org_id},
        )

        # Insert Default File Connector Data Source
        await session.execute(
            text("""
            INSERT INTO data_sources (id, organization_id, name, source_type, external_id, authority_level, status)
            VALUES (:id, :org_id, 'File Upload Connector', 'file', 'file-upload-connector', 85, 'active')
            ON CONFLICT (id) DO NOTHING;
            """),
            {"id": source_id, "org_id": org_id},
        )

        await session.commit()
        print("Database purge and canonical reset complete.")

        # 3. Print verified table counts
        res = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        )
        tables = [r[0] for r in res.fetchall()]
        print("\nCurrent Table Row Counts:")
        for t in tables:
            try:
                cnt = await session.execute(text(f'SELECT count(*) FROM "{t}"'))
                print(f"  {t}: {cnt.scalar()} rows")
            except Exception as e:
                pass


if __name__ == "__main__":
    asyncio.run(purge_all_data())
