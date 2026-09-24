import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.llm.mock_provider import MockLLMProvider
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.conflict_service import ConflictService
from app.services.trust_service import TrustService


async def extract_all_current():
    async with AsyncSessionLocal() as session:
        mock_llm = MockLLMProvider()
        ext_service = ClaimExtractionService(session, llm_provider=mock_llm)
        conf_service = ConflictService(session, llm_provider=mock_llm)
        trust_service = TrustService(session)

        res = await session.execute(select(DocumentVersion).where(DocumentVersion.is_current == True))
        versions = res.scalars().all()
        print(f"Found {len(versions)} current document versions to process.")

        for v in versions:
            doc = await session.get(Document, v.document_id)
            title = doc.title if doc else str(v.id)
            print(f"\nExtracting claims for: {title}...")
            claims = await ext_service.extract_claims_from_version(v.id)
            print(f"  -> Extracted {len(claims)} atomic claims.")
            
            print(f"Running conflict detection for: {title}...")
            conflicts = await conf_service.run_conflict_detection_for_version(v.id)
            print(f"  -> Detected {len(conflicts)} conflicts.")

            print(f"Calculating multi-factor trust scores...")
            await trust_service.calculate_for_version(v.id)

        await session.commit()
        print("\nAll current documents processed successfully!")


if __name__ == "__main__":
    asyncio.run(extract_all_current())
