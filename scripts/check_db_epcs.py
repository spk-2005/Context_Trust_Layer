import asyncio, sys
sys.path.insert(0, 'backend')
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, title FROM documents WHERE title ILIKE '%Electronic Prescriptions%' OR title ILIKE '%EPCS%'"))
        docs = res.fetchall()
        print('Matching docs:', docs)
        for d in docs:
            v_res = await db.execute(text("SELECT id, version_number FROM document_versions WHERE document_id = :d_id"), {'d_id': d[0]})
            versions = v_res.fetchall()
            print(f'Versions for {d[0]}:', versions)
            for v in versions:
                c_res = await db.execute(text("SELECT count(*) FROM claims WHERE document_version_id = :v_id"), {'v_id': v[0]})
                c_count = c_res.scalar()
                print(f'Claims for version {v[0]}: {c_count}')

asyncio.run(check())
