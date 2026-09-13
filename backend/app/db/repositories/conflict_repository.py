import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ConflictStatus
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.repositories.base import BaseRepository


class ConflictRepository(BaseRepository[ClaimConflict]):
    def __init__(self, session: AsyncSession):
        super().__init__(ClaimConflict, session)

    async def list_by_claim(
        self,
        claim_id: uuid.UUID,
    ) -> Sequence[ClaimConflict]:
        stmt = (
            select(ClaimConflict)
            .where(
                or_(
                    ClaimConflict.claim_a_id == claim_id,
                    ClaimConflict.claim_b_id == claim_id,
                )
            )
            .options(
                selectinload(ClaimConflict.claim_a),
                selectinload(ClaimConflict.claim_b),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_pending_review(
        self,
        organization_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ClaimConflict]:
        stmt = (
            select(ClaimConflict)
            .where(
                ClaimConflict.resolution_status
                == ConflictStatus.HUMAN_REVIEW_REQUIRED
            )
        )
        if organization_id:
            stmt = stmt.join(ClaimConflict.claim_a).where(
                Claim.organization_id == organization_id
            )
        stmt = stmt.options(
            selectinload(ClaimConflict.claim_a).selectinload(Claim.validity_records),
            selectinload(ClaimConflict.claim_a).selectinload(Claim.trust_scores),
            selectinload(ClaimConflict.claim_a).selectinload(Claim.evidence),
            selectinload(ClaimConflict.claim_b).selectinload(Claim.validity_records),
            selectinload(ClaimConflict.claim_b).selectinload(Claim.trust_scores),
            selectinload(ClaimConflict.claim_b).selectinload(Claim.evidence),
        )
        result = await self.session.execute(stmt)
        all_conflicts = result.scalars().all()

        # Deduplicate semantically: ensure unique (text_a, text_b) pairs in queue
        seen_pairs: set[tuple[str, str]] = set()
        deduped: list[ClaimConflict] = []
        for c in all_conflicts:
            if not c.claim_a or not c.claim_b:
                continue
            ta = " ".join(c.claim_a.claim_text.strip().lower().split())
            tb = " ".join(c.claim_b.claim_text.strip().lower().split())
            pair_key = (min(ta, tb), max(ta, tb))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            deduped.append(c)

        return deduped[offset : offset + limit]
