from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.context import ContextQueryRequest, ContextQueryResponse

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/query", response_model=ContextQueryResponse)
async def query_trusted_context(
    req: ContextQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Query trusted context for an AI agent (ready for downstream retrieval engine)."""
    return ContextQueryResponse(
        context=[],
        conflicts=[],
        confidence=req.min_trust_score,
    )
