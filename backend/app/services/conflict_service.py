import decimal
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conflict_engine.detector import ConflictDetector
from app.db.enums import ClaimStatus, ConflictStatus, ReviewDecision
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.human_review import HumanReview
from app.db.repositories.conflict_repository import ConflictRepository


class ConflictService:
    """Service for running conflict detection and recording human resolutions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.detector = ConflictDetector(session)
        self.conflict_repo = ConflictRepository(session)

    async def run_conflict_detection_for_version(
        self,
        document_version_id: uuid.UUID,
    ) -> Sequence[ClaimConflict]:
        stmt = select(Claim).where(Claim.document_version_id == document_version_id)
        res = await self.session.execute(stmt)
        claims = res.scalars().all()

        conflicts: list[ClaimConflict] = []
        for claim in claims:
            found = await self.detector.detect_conflicts_for_claim(claim)
            conflicts.extend(found)

        return conflicts

    async def resolve_conflict(
        self,
        conflict_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        decision: ReviewDecision,
        chosen_claim_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> ClaimConflict:
        """Resolve a conflict with an audit trail in human_reviews."""
        conflict = await self.session.get(ClaimConflict, conflict_id)
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found.")

        claim_a = await self.session.get(Claim, conflict.claim_a_id)
        claim_b = await self.session.get(Claim, conflict.claim_b_id)

        from app.services.trust_service import TrustService

        chosen_uuid = uuid.UUID(str(chosen_claim_id)) if chosen_claim_id else None
        reviewer_uuid = uuid.UUID(str(reviewer_id))

        # Update conflict status
        conflict.resolution_status = ConflictStatus.RESOLVED
        conflict.resolved_claim_id = chosen_uuid
        conflict.resolved_by = reviewer_uuid
        conflict.resolved_at = datetime.now(timezone.utc)

        # Update claim statuses based on decision
        if decision == ReviewDecision.APPROVE and chosen_uuid:
            if claim_a and claim_a.id == chosen_uuid:
                claim_a.status = ClaimStatus.VERIFIED
                if claim_b:
                    claim_b.status = ClaimStatus.OUTDATED
            elif claim_b and claim_b.id == chosen_uuid:
                claim_b.status = ClaimStatus.VERIFIED
                if claim_a:
                    claim_a.status = ClaimStatus.OUTDATED
            else:
                raise ValueError(
                    f"Chosen claim {chosen_uuid} is not part of this conflict (claims: {claim_a.id if claim_a else None}, {claim_b.id if claim_b else None})"
                )
        elif decision == ReviewDecision.REJECT:
            if claim_a:
                claim_a.status = ClaimStatus.REJECTED
            if claim_b:
                claim_b.status = ClaimStatus.REJECTED

        # Record audit log
        org_id = claim_a.organization_id if claim_a else claim_b.organization_id
        review = HumanReview(
            organization_id=org_id,
            reviewer_id=reviewer_uuid,
            target_type="claim_conflict",
            target_id=conflict.id,
            decision=decision,
            reason=reason,
        )
        self.session.add(review)
        await self.session.flush()

        # Recalculate trust scores for both claims
        trust_service = TrustService(self.session)
        if claim_a:
            await trust_service.calculate_for_claim(claim_a.id)
        if claim_b:
            await trust_service.calculate_for_claim(claim_b.id)

        await self.session.flush()
        await self.session.refresh(conflict)
        return conflict
