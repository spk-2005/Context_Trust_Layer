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
