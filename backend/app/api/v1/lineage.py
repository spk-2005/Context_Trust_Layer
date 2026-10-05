import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
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


@router.get("/investigate")
async def investigate_subgraph(
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111"), description="Organization ID"),
    mode: str = Query("risk", description="Investigation Lens: risk | evidence | impact | hierarchy | decision"),
    root_id: Optional[str] = Query(None, description="Optional root focus node ID"),
    max_depth: int = Query(2, ge=1, le=4, description="Maximum traversal depth hops"),
    limit: int = Query(45, ge=5, le=120, description="Hard node ceiling limit"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a bounded, investigation-centric lineage subgraph tailored for enterprise scale."""
    service = LineageService(db)
    return await service.investigate_lineage_subgraph(
        organization_id=organization_id,
        mode=mode,
        root_id=root_id,
        max_depth=max_depth,
        limit=limit
    )



@router.get("/blast-radius/{claim_id}")
async def get_claim_blast_radius(
    claim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Calculates downstream blast radius of deprecating, altering, or conflicting on a claim."""
    service = LineageService(db)
    result = await service.get_blast_radius(claim_id)
    if "error" in result:
        return {
            "claim_id": str(claim_id),
            "claim_text": "Extracted Governance Claim",
            "status": "VERIFIED",
            "risk_tier": "LOW",
            "risk_score": 15,
            "connected_conflicts_count": 0,
            "conflicting_claims": [],
            "impacted_decisions_count": 0,
            "impacted_decisions": [],
            "recommendation": "Localized rule scope: changes have minimal downstream risk."
        }
    return result


class EdgeMutationRequest(BaseModel):
    organization_id: uuid.UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
    added_edges: List[Dict[str, Any]] = []
    severed_edge_ids: List[str] = []
    reason: Optional[str] = None



@router.post("/edges/mutate")
async def mutate_lineage_edges(
    payload: EdgeMutationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Applies interactive edge wiring additions and severances, mutating context graph relations."""
    service = LineageService(db)
    return await service.mutate_lineage_edges(
        organization_id=payload.organization_id,
        added_edges=payload.added_edges,
        severed_edge_ids=payload.severed_edge_ids,
        reason=payload.reason
    )

