import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal, engine
from app.db.base import Base
# Import all models to register in metadata
import app.db.models  # noqa


async def migrate():
    print("Running Phase 3 database migrations...")
    async with AsyncSessionLocal() as session:
        # 1. Add domain_whitelist column if not exists
        await session.execute(text("""
            ALTER TABLE organizations 
            ADD COLUMN IF NOT EXISTS domain_whitelist JSON DEFAULT '[]'::json;
        """))
        print("[OK] organizations.domain_whitelist column ensured")

        # 2. Add allowed_auth_methods column if not exists
        await session.execute(text("""
            ALTER TABLE organizations 
            ADD COLUMN IF NOT EXISTS allowed_auth_methods JSON DEFAULT '["password", "google", "microsoft", "okta"]'::json;
        """))
        print("[OK] organizations.allowed_auth_methods column ensured")

        # 3. Create organization_invites table if not exists
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_invites (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                email VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'developer',
                token VARCHAR(255) NOT NULL UNIQUE,
                invited_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_org_invites_org ON organization_invites(organization_id)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_org_invites_token ON organization_invites(token)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_org_invites_email ON organization_invites(email)"))
        print("[OK] organization_invites table and indexes ensured")

        # 4. Populate domain_whitelist for SSFA Capital Holdings if empty
        await session.execute(text("""
            UPDATE organizations
            SET domain_whitelist = '["ssfa.com", "ssfacapital.com"]'::json
            WHERE slug = 'ssfa-capital' OR name ILIKE '%SSFA%'
               OR slug = 'ssfa-com';
        """))

        await session.commit()
        print("[DONE] Phase 3 database migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
