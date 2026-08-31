import decimal
import uuid
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ClaimStatus, ConflictStatus
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider


class ConflictDetector:
    """Detects semantic and logical contradictions between claims across documents."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.llm = llm_provider or get_llm_provider()

    async def detect_conflicts_for_claim(
        self,
        target_claim: Claim,
    ) -> Sequence[ClaimConflict]:
        """Compare target_claim against all other active claims in the same organization."""
        detected_conflicts: list[ClaimConflict] = []

        # Find potential candidate claims (same org, different claim, active)
        stmt = (
            select(Claim)
            .where(
                Claim.organization_id == target_claim.organization_id,
                Claim.id != target_claim.id,
            )
            .options(selectinload(Claim.document_version))
        )
        res = await self.session.execute(stmt)
        candidates = res.scalars().all()

        for cand in candidates:
            # Check if conflict already logged for this pair
            pair_stmt = select(ClaimConflict).where(
                or_(
                    (ClaimConflict.claim_a_id == target_claim.id) & (ClaimConflict.claim_b_id == cand.id),
                    (ClaimConflict.claim_a_id == cand.id) & (ClaimConflict.claim_b_id == target_claim.id),
                )
            )
            pair_res = await self.session.execute(pair_stmt)
            if pair_res.scalar_one_or_none():
                continue

            # Evaluate contradiction via LLM / logic
            eval_res = await self.llm.evaluate_contradiction(
                claim_a_text=target_claim.claim_text,
                claim_b_text=cand.claim_text,
            )

            if eval_res.is_contradiction:
                # Ensure ordered UUIDs for deterministic pair constraint
                claim_a_id = target_claim.id
                claim_b_id = cand.id

                conflict = ClaimConflict(
                    claim_a_id=claim_a_id,
                    claim_b_id=claim_b_id,
                    conflict_type=eval_res.conflict_type,
                    severity=eval_res.severity,
                    confidence=decimal.Decimal(f"{eval_res.confidence:.4f}"),
                    resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
                )
                self.session.add(conflict)

                # Mark claims as conflicted
                target_claim.status = ClaimStatus.CONFLICTED
                cand.status = ClaimStatus.CONFLICTED

                detected_conflicts.append(conflict)

        if detected_conflicts:
            await self.session.flush()

        return detected_conflicts

    async def detect_all_organization_conflicts(
        self,
        organization_id: uuid.UUID,
    ) -> Sequence[ClaimConflict]:
        stmt = select(Claim).where(Claim.organization_id == organization_id)
        res = await self.session.execute(stmt)
        claims = res.scalars().all()

        all_conflicts: list[ClaimConflict] = []
        for claim in claims:
            conflicts = await self.detect_conflicts_for_claim(claim)
            all_conflicts.extend(conflicts)

        return all_conflicts
