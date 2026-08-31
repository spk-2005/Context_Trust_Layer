import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.enums import ClaimStatus
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
    db: AsyncSession = Depends(get_db),
):
    """Extract claims from a document version, calculate trust scores, and run conflict checks."""
    extraction_service = ClaimExtractionService(db)
    trust_service = TrustService(db)
    conflict_service = ConflictService(db)
    claim_repo = ClaimRepository(db)

    # 1. Extract claims
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
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = ClaimRepository(db)
    claims = await repo.list_by_organization(
        organization_id=organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [ClaimResponse.model_validate(c) for c in claims]
