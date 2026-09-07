import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.conflict_repository import ConflictRepository
from app.schemas.conflict import ConflictResolveRequest, ConflictResponse
from app.services.conflict_service import ConflictService

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("/pending", response_model=list[ConflictResponse])
async def list_pending_conflicts(
    organization_id: uuid.UUID | None = Query(None, description="Optional organization ID filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = ConflictRepository(db)
    conflicts = await repo.list_pending_review(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    return [ConflictResponse.model_validate(c) for c in conflicts]


@router.post("/re-evaluate")
async def re_evaluate_conflicts(
    organization_id: uuid.UUID | None = Query(None, description="Optional organization ID filter"),
    db: AsyncSession = Depends(get_db),
):
    """Re-evaluate all pending conflicts against the current context-aware contradiction rules and purge false positives."""
    service = ConflictService(db)
    result = await service.re_evaluate_all_pending(organization_id=organization_id)
    return {
        "status": "success",
        "purged_false_positives": result["purged"],
        "retained_conflicts": result["retained"],
        "message": f"Purged {result['purged']} false-positive conflicts. Retained {result['retained']} genuine conflicts.",
    }


@router.post("/{conflict_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    req: ConflictResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ConflictService(db)
    conflict = await service.resolve_conflict(
        conflict_id=conflict_id,
        reviewer_id=req.reviewer_id,
        decision=req.decision,
        chosen_claim_id=req.chosen_claim_id,
        reason=req.reason,
    )
    await db.commit()
    return ConflictResponse.model_validate(conflict)



