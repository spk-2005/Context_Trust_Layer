import decimal
import uuid
import pytest
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ConflictStatus, ReviewDecision
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.human_review import HumanReview
from app.db.models.organization import Organization
from app.db.repositories.data_source_repository import DataSourceRepository
from app.services.conflict_service import ConflictService


@pytest.mark.asyncio
async def test_auto_resolve_conflicts_end_to_end():
    """Verify that auto_resolve_conflicts sweeps pending conflicts, applies precedence, and updates audit records."""
    async with AsyncSessionLocal() as db_session:
        uid = uuid.uuid4().hex[:6]
        org = Organization(name=f"Auto Resolve Org {uid}", slug=f"auto-resolve-org-{uid}")
        db_session.add(org)
        await db_session.flush()

        ds_repo = DataSourceRepository(db_session)
        ds = await ds_repo.get_or_create(
            organization_id=org.id,
            name="Policy Portal",
            source_type="file_upload",
            external_id=f"policy-{uid}",
            authority_level=85,
        )

        doc = Document(organization_id=org.id, source_id=ds.id, title="Enterprise Governance Policy")
        db_session.add(doc)
        await db_session.flush()

        v1 = DocumentVersion(document_id=doc.id, version_number=1, is_current=False)
        v2 = DocumentVersion(document_id=doc.id, version_number=2, is_current=True)
        db_session.add_all([v1, v2])
        await db_session.flush()

        claim_v1 = Claim(
            organization_id=org.id,
            document_version_id=v1.id,
            claim_text="Legacy refund policy allows 14 days.",
            subject="Refund Policy",
            status=ClaimStatus.CONFLICTED,
        )
        claim_v2 = Claim(
            organization_id=org.id,
            document_version_id=v2.id,
            claim_text="Current refund policy allows 30 days under active governance.",
            subject="Refund Policy",
            status=ClaimStatus.CONFLICTED,
        )
        db_session.add_all([claim_v1, claim_v2])
        await db_session.flush()

        conflict = ClaimConflict(
            claim_a_id=claim_v1.id,
            claim_b_id=claim_v2.id,
            conflict_type="numerical_discrepancy",
            severity="high",
            confidence=decimal.Decimal("0.9200"),
            resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
        )
        db_session.add(conflict)
        await db_session.commit()

        # Execute Autonomous Conflict Resolution
        service = ConflictService(db_session)
        result = await service.auto_resolve_conflicts(organization_id=org.id)

        assert result["status"] == "success"
        assert result["auto_resolved_count"] == 1
        assert result["remaining_pending_count"] == 0

        # Verify conflict status updated
        await db_session.refresh(conflict)
        assert conflict.resolution_status == ConflictStatus.RESOLVED
        assert conflict.resolved_claim_id == claim_v2.id

        # Verify claim statuses
        await db_session.refresh(claim_v1)
        await db_session.refresh(claim_v2)
        assert claim_v2.status == ClaimStatus.VERIFIED
        assert claim_v1.status == ClaimStatus.OUTDATED

        # Verify HumanReview audit record created
        rev_stmt = select(HumanReview).where(HumanReview.target_id == conflict.id)
        rev_res = await db_session.execute(rev_stmt)
        review = rev_res.scalar_one_or_none()
        assert review is not None
        assert review.decision == ReviewDecision.APPROVE
        assert "Autonomous Precedence Engine" in review.reason
