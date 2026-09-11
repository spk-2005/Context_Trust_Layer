import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.lineage_service import LineageService

router = APIRouter(prefix="/lineage", tags=["lineage"])


@router.get("/graph")
async def get_lineage_graph(
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111"), description="Organization ID"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full multi-tiered DAG lineage graph across sources, documents, claims, conflicts, and decisions."""
    service = LineageService(db)
    return await service.get_lineage_graph(organization_id)


@router.get("/blast-radius/{claim_id}")
async def get_claim_blast_radius(
    claim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Calculates downstream blast radius of deprecating, altering, or conflicting on a claim."""
    service = LineageService(db)
    result = await service.get_blast_radius(claim_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result
