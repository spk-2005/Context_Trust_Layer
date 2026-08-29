import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ConflictStatus
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
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ClaimConflict]:
        stmt = (
            select(ClaimConflict)
            .where(
                ClaimConflict.resolution_status
                == ConflictStatus.HUMAN_REVIEW_REQUIRED
            )
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(ClaimConflict.claim_a),
                selectinload(ClaimConflict.claim_b),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
