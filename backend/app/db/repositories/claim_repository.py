import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.repositories.base import BaseRepository


class ClaimRepository(BaseRepository[Claim]):
    def __init__(self, session: AsyncSession):
        super().__init__(Claim, session)

    async def get_with_details(self, claim_id: uuid.UUID) -> Claim | None:
        stmt = (
            select(Claim)
            .where(Claim.id == claim_id)
            .options(
                selectinload(Claim.evidence),
                selectinload(Claim.validity_records),
                selectinload(Claim.trust_scores),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_version(
        self,
        document_version_id: uuid.UUID,
    ) -> Sequence[Claim]:
        stmt = (
            select(Claim)
            .where(Claim.document_version_id == document_version_id)
            .options(
                selectinload(Claim.evidence),
                selectinload(Claim.validity_records),
                selectinload(Claim.trust_scores),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        status: ClaimStatus | None = None,
        canonical_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Claim]:
        stmt = select(Claim).where(Claim.organization_id == organization_id)
        if status:
            stmt = stmt.where(Claim.status == status)
        if canonical_only:
            stmt = stmt.where(Claim.claim_type != "derived_summary")
        stmt = stmt.offset(offset).limit(limit).options(
            selectinload(Claim.evidence),
            selectinload(Claim.validity_records),
            selectinload(Claim.trust_scores),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
