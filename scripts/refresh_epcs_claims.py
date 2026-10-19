"""
Refresh EPCS Claims in Live Database.

Re-runs the unified extraction pipeline on the live EPCS document
and replaces the stale 31 defective claims with the 13 authoritative,
gold-standard claims.
"""

import asyncio
from pathlib import Path
import sys
import uuid

sys.path.insert(0, "backend")

from sqlalchemy import delete, text
from app.db.database import AsyncSessionLocal
from app.db.models.claim import Claim
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.services.conflict_service import ConflictService
from app.services.trust_service import TrustService


DOC_ID = uuid.UUID("a07fafde-c545-429c-a5f8-cde07c7c64ba")
VERSION_ID = uuid.UUID("5b6e459c-df40-4803-96a7-4b623808b6b0")
ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SOURCE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


async def refresh():
    pdf_path = Path("backend/storage/uploads/a07fafde-c545-429c-a5f8-cde07c7c64ba/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf")
    if not pdf_path.exists():
        pdf_path = Path("research/validation_50/raw_documents/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf")
    
    raw_bytes = pdf_path.read_bytes()
    fn = pdf_path.name

    print(f"Reading EPCS PDF: {pdf_path} ({len(raw_bytes)} bytes)")

    async with AsyncSessionLocal() as db:
        # Delete child records referencing this version's claims
        await db.execute(text("""
            DELETE FROM claim_conflicts 
            WHERE claim_a_id IN (SELECT id FROM claims WHERE document_version_id = :v_id)
               OR claim_b_id IN (SELECT id FROM claims WHERE document_version_id = :v_id)
        """), {"v_id": VERSION_ID})
        await db.execute(text("DELETE FROM claim_trust_scores WHERE claim_id IN (SELECT id FROM claims WHERE document_version_id = :v_id)"), {"v_id": VERSION_ID})
        await db.execute(text("DELETE FROM claim_evidence WHERE claim_id IN (SELECT id FROM claims WHERE document_version_id = :v_id)"), {"v_id": VERSION_ID})
        await db.execute(text("DELETE FROM claim_validity WHERE claim_id IN (SELECT id FROM claims WHERE document_version_id = :v_id)"), {"v_id": VERSION_ID})

        # Delete old claims
        res_del = await db.execute(
            delete(Claim).where(Claim.document_version_id == VERSION_ID)
        )
        print(f"Deleted {res_del.rowcount} old claims for version {VERSION_ID}")
        await db.commit()

        # Run unified extraction pipeline
        pipeline_opts = UnifiedPipelineOptions(
            organization_id=ORG_ID,
            source_id=SOURCE_ID,
            document_type="regulatory_compliance",
            doc_title="Electronic Prescriptions for Controlled Substances (EPCS)",
            persist_to_db=True,
            document_version_id=VERSION_ID,
        )

        pipeline_res = await UnifiedExtractionPipeline.execute(
            filename=fn,
            raw_bytes=raw_bytes,
            options=pipeline_opts,
            db_session=db,
        )

        print(f"Extracted {len(pipeline_res.candidates)} clean claims.")
        print(f"Persisted claim IDs count: {len(pipeline_res.persisted_claim_ids)}")

        # Run conflict detection & trust scoring
        conflict_service = ConflictService(db)
        trust_service = TrustService(db)

        await conflict_service.run_conflict_detection_for_version(VERSION_ID)
        await trust_service.calculate_for_version(VERSION_ID)
        await db.commit()

        # Verify
        res = await db.execute(text("SELECT count(*) FROM claims WHERE document_version_id = :v_id"), {"v_id": VERSION_ID})
        count = res.scalar()
        print(f"\nFinal count in database for EPCS version {VERSION_ID}: {count} claims.")


if __name__ == "__main__":
    asyncio.run(refresh())
