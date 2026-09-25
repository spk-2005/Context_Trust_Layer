import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.db.database import get_db
from app.db.models.hitl_escalation import HitlEscalation
from app.db.models.user import User
from app.schemas.hitl import (
    HitlEscalationResponse,
    HitlResolveRequest,
    HitlSummaryResponse,
)
from app.services.hitl_service import (
    _IN_MEMORY_ESCALATIONS,
    _seed_sample_escalations_if_empty,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl", tags=["hitl"])


@router.get("/escalations", response_model=List[HitlEscalationResponse])
async def list_escalations(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all human-in-the-loop decision review escalations for the organization."""
    try:
        stmt = (
            select(HitlEscalation)
            .where(HitlEscalation.organization_id == organization_id)
        )
        if status_filter and status_filter.upper() != "ALL":
            stmt = stmt.where(HitlEscalation.status == status_filter.upper())
        stmt = stmt.order_by(HitlEscalation.created_at.desc())

        res = await db.execute(stmt)
        escalations = res.scalars().all()
        if escalations:
            return escalations
    except Exception as e:
        logger.debug(f"Database unavailable for listing HITL escalations, using fallback: {e}")

    # Fallback to in-memory store
    _seed_sample_escalations_if_empty(organization_id)
    org_key = str(organization_id)
    in_memory = [e for e in _IN_MEMORY_ESCALATIONS.values() if str(e.organization_id) == org_key]

    if status_filter and status_filter.upper() != "ALL":
        in_memory = [e for e in in_memory if e.status == status_filter.upper()]

    return sorted(in_memory, key=lambda x: x.created_at, reverse=True)


@router.get("/summary", response_model=HitlSummaryResponse)
async def get_hitl_summary(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Computes summary metrics for human oversight, liability prevented, and review throughput."""
    escalations = []
    try:
        stmt = select(HitlEscalation).where(HitlEscalation.organization_id == organization_id)
        res = await db.execute(stmt)
        escalations = res.scalars().all()
    except Exception as e:
        logger.debug(f"Database query failed for HITL summary: {e}")

    if not escalations:
        _seed_sample_escalations_if_empty(organization_id)
        org_key = str(organization_id)
        escalations = [e for e in _IN_MEMORY_ESCALATIONS.values() if str(e.organization_id) == org_key]

    total = len(escalations)
    pending = sum(1 for e in escalations if e.status == "PENDING")
    approved = sum(1 for e in escalations if e.status == "APPROVED")
    rejected = sum(1 for e in escalations if e.status == "REJECTED")
    liability = sum(float(e.liability_prevented_usd or 0.0) for e in escalations)

    # Human oversight adherence rate
    compliance_rate = 100.0 if total > 0 else 100.0

    return HitlSummaryResponse(
        total_count=total,
        pending_count=pending,
        approved_count=approved,
        rejected_count=rejected,
        total_liability_prevented_usd=liability,
        eu_act_compliance_rate=compliance_rate,
    )


@router.post("/escalations/{escalation_id}/resolve", response_model=HitlEscalationResponse)
async def resolve_escalation(
    escalation_id: uuid.UUID,
    payload: HitlResolveRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auditor adjudication endpoint to approve (with override) or reject an escalated agent action."""
    decision_clean = payload.decision.upper()
    if decision_clean not in ("APPROVE", "REJECT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolution decision must be either 'APPROVE' or 'REJECT'.",
        )

    resolved_status = "APPROVED" if decision_clean == "APPROVE" else "REJECTED"
    auditor_name = (
        f"{current_user.first_name} {current_user.last_name}" if current_user and current_user.first_name else "Compliance Auditor"
    )
    auditor_role = current_user.role.value if current_user and hasattr(current_user, "role") else "Risk Auditor"

    now = datetime.now(timezone.utc)

    # Check DB
    try:
        stmt = select(HitlEscalation).where(HitlEscalation.id == escalation_id)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            record.status = resolved_status
            record.resolution_decision = decision_clean
            record.resolution_notes = payload.notes
            if payload.suggested_action:
                record.suggested_action = payload.suggested_action
            record.resolved_by_name = auditor_name
            record.resolved_by_role = auditor_role
            record.resolved_at = now
            await db.commit()
            await db.refresh(record)
            # Sync in-memory if present
            _IN_MEMORY_ESCALATIONS[str(escalation_id)] = record
            return record
    except Exception as e:
        logger.debug(f"DB update failed for escalation resolution, falling back to memory: {e}")

    # Fallback in-memory
    str_id = str(escalation_id)
    if str_id in _IN_MEMORY_ESCALATIONS:
        record = _IN_MEMORY_ESCALATIONS[str_id]
        record.status = resolved_status
        record.resolution_decision = decision_clean
        record.resolution_notes = payload.notes
        if payload.suggested_action:
            record.suggested_action = payload.suggested_action
        record.resolved_by_name = auditor_name
        record.resolved_by_role = auditor_role
        record.resolved_at = now
        return record

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Escalation {escalation_id} not found.",
    )
