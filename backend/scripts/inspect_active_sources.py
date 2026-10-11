import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import AsyncSessionLocal
from app.db.models.document import Document
from app.db.models.data_source import DataSource
from sqlalchemy import select, func


async def main():
    async with AsyncSessionLocal() as session:
        # Check sources
        res = await session.execute(select(DataSource))
        sources = res.scalars().all()
        print(f"Total Sources in DB: {len(sources)}")
        for s in sources:
            if s.status == "active":
                print(f"Active Source: [{s.source_type}] {s.name} (ID: {s.id})")

        # Check documents
        doc_res = await session.execute(
            select(Document.source_id, func.count(Document.id), func.min(Document.title))
            .group_by(Document.source_id)
        )
        print("\nDocuments in DB grouped by source_id:")
        for r in doc_res.all():
            print(f"  Source {r[0]}: {r[1]} docs (Sample: '{r[2]}')")


if __name__ == "__main__":
    asyncio.run(main())
