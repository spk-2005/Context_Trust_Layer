import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.database import get_db
from app.db.enums import ClaimStatus
from app.db.models.user import User
from app.db.repositories.claim_repository import ClaimRepository
from app.db.repositories.document_repository import DocumentRepository
from app.schemas.claim import ClaimResponse
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.conflict_service import ConflictService
from app.services.trust_service import TrustService

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post(
    "/extract/{document_version_id}",
    response_model=list[ClaimResponse],
    status_code=status.HTTP_201_CREATED,
)
async def extract_and_score_claims(
    document_version_id: uuid.UUID,
    use_mock: bool = Query(
        False,
        description=(
            "Set true to use the fast deterministic MockLLMProvider instead of Ollama. "
            "Useful for quick testing - returns instantly without calling the LLM server."
        ),
    ),
    user_role: str = Query(default="data_owner", description="Role of acting user"),
    _authorized_user: Optional[User] = Depends(require_permission(Permission.CLAIMS_EXTRACT)),
    db: AsyncSession = Depends(get_db),
):
    """Extract claims from a document version, calculate trust scores, and run conflict checks.

    - use_mock=false (default): calls Ollama with qwen3:1.7b - real LLM extraction,
      expect 20-60 s for a typical policy document.
    - use_mock=true: uses fast rule-based MockLLMProvider - returns in < 1 s,
      ideal for Swagger demos and pipeline smoke-tests.
    """
    if use_mock:
        from app.llm.mock_provider import MockLLMProvider
        llm_provider = MockLLMProvider()
    else:
        llm_provider = None  # factory picks up OllamaProvider from .env

    extraction_service = ClaimExtractionService(db, llm_provider=llm_provider)
    trust_service = TrustService(db)
    conflict_service = ConflictService(db, llm_provider=llm_provider)
    claim_repo = ClaimRepository(db)

    from app.db.models.document_version import DocumentVersion

    # 0. Resolve document_version_id if a document_id was passed
    ver_obj = await db.get(DocumentVersion, document_version_id)
    if not ver_obj:
        doc_repo = DocumentRepository(db)
        cur_ver = await doc_repo.get_current_version(document_version_id)
        if cur_ver:
            document_version_id = cur_ver.id

    # 1. Extract claims (parallel across sections)
    try:
        extracted = await extraction_service.extract_claims_from_version(document_version_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # 2. Run conflict detection against existing claims
    await conflict_service.run_conflict_detection_for_version(document_version_id)

    # 3. Compute trust scores
    await trust_service.calculate_for_version(document_version_id)

    await db.commit()

    # 4. Fetch full claim records with loaded relations
    full_claims = await claim_repo.list_by_version(document_version_id)
    return [ClaimResponse.model_validate(c) for c in full_claims]


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = ClaimRepository(db)
    claim = await repo.get_with_details(claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return ClaimResponse.model_validate(claim)


@router.get("", response_model=list[ClaimResponse])
async def list_claims(
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    status: ClaimStatus | None = Query(None, description="Filter by claim status"),
    canonical_only: bool = Query(False, description="Filter to return only canonical operative rules, excluding summaries"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = ClaimRepository(db)
    claims = await repo.list_by_organization(
        organization_id=organization_id,
        status=status,
        canonical_only=canonical_only,
        limit=limit,
        offset=offset,
    )
    return [ClaimResponse.model_validate(c) for c in claims]


@router.get("/lifecycle-summary", status_code=status.HTTP_200_OK)
async def get_claims_lifecycle_summary(
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
):
    """Layer 6: Returns enterprise claim lifecycle status breakdown and trust metrics."""
    from sqlalchemy import func, select
    from app.db.models.claim import Claim
    from app.db.models.claim_trust_score import ClaimTrustScore

    status_counts_stmt = (
        select(Claim.status, func.count(Claim.id))
        .where(Claim.organization_id == organization_id)
        .group_by(Claim.status)
    )
    status_counts_res = await db.execute(status_counts_stmt)
    status_breakdown = {str(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in status_counts_res.all()}

    avg_score_stmt = (
        select(func.avg(ClaimTrustScore.overall_score))
        .join(Claim, Claim.id == ClaimTrustScore.claim_id)
        .where(Claim.organization_id == organization_id)
    )
    avg_score = (await db.execute(avg_score_stmt)).scalar() or 0.0

    total_claims = sum(status_breakdown.values())
    return {
        "organization_id": str(organization_id),
        "total_claims": total_claims,
        "status_breakdown": status_breakdown,
        "approved_claims": status_breakdown.get("verified", 0) + status_breakdown.get("active", 0),
        "review_queued_claims": status_breakdown.get("candidate", 0),
        "rejected_claims": status_breakdown.get("rejected", 0),
        "average_trust_score": round(float(avg_score), 4),
    }

