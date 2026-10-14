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

    async def supersede_claims_for_document(
        self,
        document_id: uuid.UUID,
        new_version_id: uuid.UUID | None = None,
    ) -> int:
        """
        Transitions active/verified/candidate claims from superseded versions of a document
        to ClaimStatus.SUPERSEDED, and sets is_current=False and valid_until=now on ClaimValidity.
        Preserves complete historical audit trail without hard deletion.
        """
        from datetime import datetime, timezone
        from sqlalchemy import update
        from app.db.models.document_version import DocumentVersion

        # 1. Find claim IDs from older versions
        query = (
            select(Claim.id)
            .join(DocumentVersion, Claim.document_version_id == DocumentVersion.id)
            .where(
                DocumentVersion.document_id == document_id,
                Claim.status.in_([ClaimStatus.VERIFIED, ClaimStatus.ACTIVE, ClaimStatus.CANDIDATE]),
            )
        )
        if new_version_id:
            query = query.where(Claim.document_version_id != new_version_id)

        res = await self.session.execute(query)
        claim_ids = [row[0] for row in res.all()]

        if not claim_ids:
            return 0

        now = datetime.now(timezone.utc)

        # 2. Update claims to SUPERSEDED
        await self.session.execute(
            update(Claim)
            .where(Claim.id.in_(claim_ids))
            .values(status=ClaimStatus.SUPERSEDED, updated_at=now)
        )

        # 3. Update validity records
        await self.session.execute(
            update(ClaimValidity)
            .where(ClaimValidity.claim_id.in_(claim_ids))
            .values(is_current=False, valid_until=now)
        )

        await self.session.flush()
        return len(claim_ids)

    @staticmethod
    def compute_claim_hash(
        document_id: str,
        version: str,
        subject: str,
        predicate: str,
        value: object,
        conditions: object = None,
    ) -> str:
        """
        Computes deterministic SHA-256 claim hash across document, version, and SPO+C.
        """
        import hashlib
        import json
        cond_str = json.dumps(conditions or [], sort_keys=True, default=str)
        raw = f"{document_id}:{version}:{subject}:{predicate}:{value}:{cond_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
