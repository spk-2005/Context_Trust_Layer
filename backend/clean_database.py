import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def clean_database():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        print("[1/3] Discovering all existing database tables...")
        res = await conn.execute(sa.text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
              AND table_name != 'alembic_version';
        """))
        tables = [r[0] for r in res.fetchall()]
        print(f"Found {len(tables)} tables: {tables}")
        
        # Truncate all tables with CASCADE including organizations to wipe everything
        if tables:
            truncate_sql = f"TRUNCATE TABLE {', '.join(tables)} CASCADE;"
            print(f"[2/3] Executing: {truncate_sql}")
            await conn.execute(sa.text(truncate_sql))
            print("Successfully wiped all existing data and companies.")
        else:
            print("[2/3] No tables found to truncate.")

        # Ensure single company named 'demo' exists
        default_org_id = "11111111-1111-1111-1111-111111111111"
        await conn.execute(sa.text(f"""
            INSERT INTO organizations (id, name, slug, created_at, updated_at)
            VALUES ('{default_org_id}', 'demo', 'demo', NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET name = 'demo', slug = 'demo', updated_at = NOW();
        """))
        print(f"[3/3] Created single client company 'demo' (ID: {default_org_id}).")
        
    await engine.dispose()
    print("\nDatabase is now completely clean with only 1 company: 'demo'!")

if __name__ == "__main__":
    asyncio.run(clean_database())
