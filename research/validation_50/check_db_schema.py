import asyncio
import sys
sys.path.insert(0, 'backend')
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'claims' ORDER BY ordinal_position;"))
        for row in res.all():
            print(f"{row[0]}: {row[1]}")

asyncio.run(main())
