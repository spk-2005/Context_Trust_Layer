import asyncio
import sys
import uuid
from sqlalchemy import text

sys.path.insert(0, 'backend')
from app.db.database import AsyncSessionLocal

async def sync():
    async with AsyncSessionLocal() as s:
        # Check current users
        users = (await s.execute(text("SELECT id, email, name FROM users"))).fetchall()
        print("Current users:", users)

        old_id = None
        for u in users:
            if u[1] == 'sarah.chen@ssfa.com' and str(u[0]) != '22222222-2222-2222-2222-222222222222':
                old_id = str(u[0])
                break

        canonical_id = '22222222-2222-2222-2222-222222222222'
        if old_id:
            print(f"Migrating Sarah Chen from {old_id} to {canonical_id}...")
            await s.execute(text("ALTER TABLE user_activity_logs DROP CONSTRAINT IF EXISTS user_activity_logs_user_id_fkey;"))
            await s.execute(text("ALTER TABLE data_sources DROP CONSTRAINT IF EXISTS data_sources_owner_id_fkey;"))
            await s.execute(text("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_owner_id_fkey;"))
            await s.execute(text("ALTER TABLE chat_sessions DROP CONSTRAINT IF EXISTS chat_sessions_user_id_fkey;"))
            await s.execute(text("ALTER TABLE claim_conflicts DROP CONSTRAINT IF EXISTS fk_conflict_resolved_by;"))
            await s.execute(text("ALTER TABLE human_reviews DROP CONSTRAINT IF EXISTS fk_human_reviews_reviewer;"))

            await s.execute(text(f"UPDATE user_activity_logs SET user_id = '{canonical_id}' WHERE user_id = '{old_id}';"))
            await s.execute(text(f"UPDATE data_sources SET owner_id = '{canonical_id}' WHERE owner_id = '{old_id}';"))
            await s.execute(text(f"UPDATE documents SET owner_id = '{canonical_id}' WHERE owner_id = '{old_id}';"))
            await s.execute(text(f"UPDATE chat_sessions SET user_id = '{canonical_id}' WHERE user_id = '{old_id}';"))
            await s.execute(text(f"UPDATE users SET id = '{canonical_id}' WHERE id = '{old_id}';"))

            await s.execute(text("ALTER TABLE user_activity_logs ADD CONSTRAINT user_activity_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;"))
            await s.execute(text("ALTER TABLE data_sources ADD CONSTRAINT data_sources_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL;"))
            await s.execute(text("ALTER TABLE documents ADD CONSTRAINT documents_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL;"))
            await s.execute(text("ALTER TABLE chat_sessions ADD CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;"))
            await s.execute(text("ALTER TABLE claim_conflicts ADD CONSTRAINT fk_conflict_resolved_by FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL;"))
            await s.execute(text("ALTER TABLE human_reviews ADD CONSTRAINT fk_human_reviews_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE RESTRICT;"))
            await s.commit()
            print("Migrated successfully.")

        org_res = await s.execute(text("SELECT id FROM organizations WHERE slug = 'demo' LIMIT 1"))
        org_id = org_res.scalar() or uuid.UUID("11111111-1111-1111-1111-111111111111")

        personas = [
            ("22222222-2222-2222-2222-222222222222", "Sarah Chen", "sarah.chen@ssfa.com", "admin", "Chief Compliance Officer", "Risk, Trust & Security"),
            ("33333333-3333-3333-3333-333333333333", "Marcus Vance", "marcus.vance@ssfa.com", "data_owner", "Principal Data Steward", "Enterprise Data Platform"),
            ("44444444-4444-4444-4444-444444444444", "Elena Rostova", "elena.rostova@ssfa.com", "reviewer", "Lead Risk Auditor", "Independent Governance & Oversight"),
            ("55555555-5555-5555-5555-555555555555", "Alex Vance", "alex.vance@ssfa.com", "developer", "Autonomous Systems Engineer", "AI Operations & Platform Engineering"),
            ("66666666-6666-6666-6666-666666666666", "Devin Zhao", "devin.zhao@regulatory-watch.org", "viewer", "Compliance Observer", "Regulatory Assurance & Oversight"),
        ]

        for pid, name, email, role, title, dept in personas:
            p_uuid = uuid.UUID(pid)
            check_u = (await s.execute(text("SELECT id FROM users WHERE id = :pid"), {"pid": p_uuid})).scalar()
            if not check_u:
                # Check by email
                by_email = (await s.execute(text("SELECT id FROM users WHERE organization_id = :org_id AND email = :email"), {"org_id": org_id, "email": email})).scalar()
                if by_email:
                    await s.execute(text("UPDATE users SET id = :pid, name = :name, role = :role, title = :title, department = :dept WHERE id = :old"), {"pid": p_uuid, "name": name, "role": role, "title": title, "dept": dept, "old": by_email})
                else:
                    await s.execute(text("""
                        INSERT INTO users (id, organization_id, name, email, role, title, department, status)
                        VALUES (:id, :org_id, :name, :email, :role, :title, :dept, 'active')
                    """), {"id": p_uuid, "org_id": org_id, "name": name, "email": email, "role": role, "title": title, "dept": dept})
            else:
                await s.execute(text("""
                    UPDATE users SET name = :name, email = :email, role = :role, title = :title, department = :dept, status = 'active'
                    WHERE id = :id
                """), {"id": p_uuid, "name": name, "email": email, "role": role, "title": title, "dept": dept})

        await s.commit()
        res = await s.execute(text("SELECT id, name, email, role FROM users ORDER BY name"))
        print("\nAll users now in DB:")
        for r in res.fetchall():
            print(" ", r)

if __name__ == "__main__":
    asyncio.run(sync())
