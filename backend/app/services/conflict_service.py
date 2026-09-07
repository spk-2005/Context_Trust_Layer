import asyncio
import decimal
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conflict_engine.detector import ConflictDetector, are_claims_topically_related
from app.db.enums import ClaimStatus, ConflictStatus, ReviewDecision
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.human_review import HumanReview
from app.db.repositories.conflict_repository import ConflictRepository
from app.llm.base import BaseLLMProvider


class ConflictService:
    """Service for running conflict detection and recording human resolutions."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.detector = ConflictDetector(session, llm_provider=llm_provider)
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

    async def re_evaluate_all_pending(
        self,
        organization_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """Re-evaluate all pending conflicts against the current evaluator rules, purging false positives."""
        stmt = (
            select(ClaimConflict)
            .where(ClaimConflict.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED)
            .options(
                selectinload(ClaimConflict.claim_a),
                selectinload(ClaimConflict.claim_b),
            )
        )
        res = await self.session.execute(stmt)
        conflicts = res.scalars().all()

        purged_count = 0
        retained_count = 0
        affected_claim_ids: set[uuid.UUID] = set()

        # Parallel evaluation of all conflicts
        async def _eval_conflict(c):
            if not c.claim_a or not c.claim_b:
                return c, None
            if not are_claims_topically_related(c.claim_a, c.claim_b):
                return c, None
            eval_res = await self.detector.llm.evaluate_contradiction(
                claim_a_text=c.claim_a.claim_text,
                claim_b_text=c.claim_b.claim_text,
            )
            return c, eval_res

        eval_pairs = await asyncio.gather(*[_eval_conflict(c) for c in conflicts], return_exceptions=False)

        for c, eval_res in eval_pairs:
            if not eval_res or not eval_res.is_contradiction:
                # Purge false-positive conflict
                affected_claim_ids.add(c.claim_a_id)
                affected_claim_ids.add(c.claim_b_id)
                await self.session.delete(c)
                purged_count += 1
            else:
                # Update conflict metadata with refreshed reasoning / confidence
                c.conflict_type = eval_res.conflict_type
                c.severity = eval_res.severity
                c.confidence = decimal.Decimal(f"{eval_res.confidence:.4f}")
                retained_count += 1

        await self.session.flush()

        # Check and reset claim statuses if they no longer have any active conflicts
        from app.services.trust_service import TrustService
        trust_service = TrustService(self.session)

        for claim_id in affected_claim_ids:
            remaining_stmt = select(ClaimConflict).where(
                or_(
                    ClaimConflict.claim_a_id == claim_id,
                    ClaimConflict.claim_b_id == claim_id,
                ),
                ClaimConflict.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED,
            )
            rem_res = await self.session.execute(remaining_stmt)
            if not rem_res.scalars().first():
                claim = await self.session.get(Claim, claim_id)
                if claim and claim.status == ClaimStatus.CONFLICTED:
                    claim.status = ClaimStatus.VERIFIED
                    await trust_service.calculate_for_claim(claim_id)

        await self.session.commit()
        return {"purged": purged_count, "retained": retained_count}

