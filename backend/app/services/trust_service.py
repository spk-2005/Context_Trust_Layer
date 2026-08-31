import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ClaimStatus, ConflictStatus
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.trust_engine.calculator import TrustScoreCalculator


class TrustService:
    """Calculates and persists trust scores for claims."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.calculator = TrustScoreCalculator()

    async def calculate_for_claim(self, claim_id: uuid.UUID) -> ClaimTrustScore:
        stmt = (
            select(Claim)
            .where(Claim.id == claim_id)
            .options(
                selectinload(Claim.document_version).selectinload(DocumentVersion.document),
                selectinload(Claim.evidence),
            )
        )
        res = await self.session.execute(stmt)
        claim = res.scalar_one_or_none()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found.")

        version = claim.document_version
        doc = version.document if version else None

        # Fetch Data Source authority
        authority_level = 50
        if doc and doc.source_id:
            ds = await self.session.get(DataSource, doc.source_id)
            if ds:
                authority_level = ds.authority_level

        # Check for unresolved conflicts
        conflicts_stmt = select(ClaimConflict).where(
            (ClaimConflict.claim_a_id == claim_id) | (ClaimConflict.claim_b_id == claim_id),
            ClaimConflict.resolution_status != ConflictStatus.RESOLVED,
        )
        conflicts_res = await self.session.execute(conflicts_stmt)
        conflicts = conflicts_res.scalars().all()
        has_conflicts = len(conflicts) > 0
        max_conflict_confidence = (
            max([float(c.confidence) for c in conflicts]) if has_conflicts else 0.0
        )

        breakdown = self.calculator.calculate(
            source_authority_level=authority_level,
            doc_created_at=version.created_at if version else None,
            has_evidence=len(claim.evidence) > 0,
            is_current_version=version.is_current if version else True,
            has_conflicts=has_conflicts,
            conflict_confidence=max_conflict_confidence,
        )

        trust_score = ClaimTrustScore(
            claim_id=claim.id,
            source_score=breakdown.source_score,
            freshness_score=breakdown.freshness_score,
            evidence_score=breakdown.evidence_score,
            consistency_score=breakdown.consistency_score,
            authority_score=breakdown.authority_score,
            human_score=breakdown.human_score,
            overall_score=breakdown.overall_score,
            scoring_model="multi_factor_trust_v1",
            scoring_version="1.0.0",
        )
        self.session.add(trust_score)

        # Update claim status if conflicted or low score, preserving human decisions
        if has_conflicts:
            claim.status = ClaimStatus.CONFLICTED
        elif claim.status in [ClaimStatus.OUTDATED, ClaimStatus.REJECTED]:
            pass  # Preserve explicit status
        elif not (version and version.is_current):
            claim.status = ClaimStatus.OUTDATED
        elif breakdown.overall_score >= 0.70:
            claim.status = ClaimStatus.VERIFIED

        await self.session.flush()
        await self.session.refresh(trust_score)
        return trust_score

    async def calculate_for_version(
        self,
        document_version_id: uuid.UUID,
    ) -> Sequence[ClaimTrustScore]:
        stmt = select(Claim.id).where(Claim.document_version_id == document_version_id)
        res = await self.session.execute(stmt)
        claim_ids = res.scalars().all()

        scores: list[ClaimTrustScore] = []
        for c_id in claim_ids:
            score = await self.calculate_for_claim(c_id)
            scores.append(score)

        return scores
