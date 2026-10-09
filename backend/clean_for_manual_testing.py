import asyncio
import os
import shutil
import uuid
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


async def clean_for_manual_testing():
    print("=" * 60)
    print("CLEANING CTL DATABASE & STORAGE FOR MANUAL TESTING")
    print("=" * 60)

    # 1. Connect to PostgreSQL
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        print("\n[1/4] Discovering and clearing database tables...")
        res = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
              AND table_name != 'alembic_version';
        """))
        tables = [r[0] for r in res.fetchall()]
        print(f"Found {len(tables)} tables to purge: {', '.join(tables)}")

        if tables:
            truncate_sql = f"TRUNCATE TABLE {', '.join(tables)} CASCADE;"
            await conn.execute(text(truncate_sql))
            print(">> Successfully truncated all tables.")

        # 2. Re-create base organization
        print("\n[2/4] Setting up clean base Organization & Personas...")
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        user_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        file_src_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")

        await conn.execute(
            text("""
            INSERT INTO organizations (id, name, slug, status, created_at, updated_at)
            VALUES (:id, 'demo', 'demo', 'active', NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET name = 'demo', slug = 'demo', status = 'active', updated_at = NOW();
            """),
            {"id": org_id},
        )

        # Base User / Admin Persona
        await conn.execute(
            text("""
            INSERT INTO users (id, organization_id, name, email, role, status, created_at, updated_at)
            VALUES (:id, :org_id, 'Sarah Chen (Lead Trust Auditor & Admin)', 'sarah.chen@demo.local', 'admin', 'active', NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET name = 'Sarah Chen (Lead Trust Auditor & Admin)', role = 'admin', status = 'active', updated_at = NOW();
            """),
            {"id": user_id, "org_id": org_id},
        )

        # Base Direct File Upload DataSource
        await conn.execute(
            text("""
            INSERT INTO data_sources (id, organization_id, name, source_type, external_id, authority_level, status, created_at, updated_at)
            VALUES (:id, :org_id, 'Direct Document Upload', 'file', 'file-upload-11111111', 85, 'active', NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET name = 'Direct Document Upload', status = 'active', updated_at = NOW();
            """),
            {"id": file_src_id, "org_id": org_id},
        )

        # Base Agent
        await conn.execute(
            text("""
            INSERT INTO agents (id, organization_id, name, description, agent_type, model_provider, model_name, status, created_at, updated_at)
            VALUES (:id, :org_id, 'Enterprise Autonomous Decision Gate Agent', 'Context Trust Gate Agent evaluating real-time claims and policies.', 'general_agent', 'ollama', 'qwen3:1.7b', 'active', NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET status = 'active', updated_at = NOW();
            """),
            {"id": agent_id, "org_id": org_id},
        )
        print(">> Created clean organization 'demo', admin user, and upload connector.")

        # 3. Verify counts
        print("\n[3/4] Verifying clean database state:")
        doc_count = (await conn.execute(text("SELECT COUNT(*) FROM documents;"))).scalar()
        claim_count = (await conn.execute(text("SELECT COUNT(*) FROM claims;"))).scalar()
        conflict_count = (await conn.execute(text("SELECT COUNT(*) FROM claim_conflicts;"))).scalar()
        print(f"  * Documents count : {doc_count}")
        print(f"  * Claims count    : {claim_count}")
        print(f"  * Conflicts count : {conflict_count}")

    await engine.dispose()

    # 4. Wipe disk storage uploads
    print("\n[4/4] Purging local uploaded files from storage...")
    storage_uploads_path = os.path.join(os.path.dirname(__file__), "storage", "uploads")
    if os.path.exists(storage_uploads_path):
        removed_count = 0
        for item in os.listdir(storage_uploads_path):
            item_path = os.path.join(storage_uploads_path, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    removed_count += 1
                else:
                    os.remove(item_path)
                    removed_count += 1
            except Exception as e:
                print(f"  Notice: Could not remove {item_path}: {e}")
        print(f">> Cleared {removed_count} files/folders from storage/uploads.")
    else:
        os.makedirs(storage_uploads_path, exist_ok=True)
        print(">> Initialized empty storage/uploads directory.")

    print("\n" + "=" * 60)
    print("SUCCESS: ENVIRONMENT IS 100% CLEAN AND READY FOR MANUAL TESTING!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(clean_for_manual_testing())
