import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        )
        tables = [r[0] for r in res.fetchall()]
        print("Found tables in public schema:")
        for t in tables:
            try:
                cnt = await session.execute(text(f'SELECT count(*) FROM "{t}"'))
                print(f"  {t}: {cnt.scalar()} rows")
            except Exception as e:
                print(f"  {t}: error {e}")


if __name__ == "__main__":
    asyncio.run(main())
