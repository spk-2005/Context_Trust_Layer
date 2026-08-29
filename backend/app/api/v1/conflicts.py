import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.conflict_repository import ConflictRepository
from app.schemas.conflict import ConflictResponse

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("/pending", response_model=list[ConflictResponse])
async def list_pending_conflicts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = ConflictRepository(db)
    conflicts = await repo.list_pending_review(limit=limit, offset=offset)
    return [ConflictResponse.model_validate(c) for c in conflicts]
