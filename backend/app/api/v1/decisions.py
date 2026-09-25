import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.decision_evaluation import DecisionEvaluation
from app.decision_engine.evaluator import DecisionEvaluator
from app.schemas.decision import (
    DecisionEvaluateRequest,
    DecisionEvaluateResponse,
    DecisionStreamItemResponse,
)
from app.services.webhook_service import dispatch_decision_event
from app.services.hitl_service import record_hitl_escalation_if_needed

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/evaluate", response_model=DecisionEvaluateResponse)
async def evaluate_decision(
    req: DecisionEvaluateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Evaluate an AI agent's intended decision and candidate evidence for validity, risk, and policy compliance."""
    evaluator = DecisionEvaluator(session=db)
    response = await evaluator.evaluate(req, session=db)

    # Dispatch incident alert if action was intercepted by policy gate
    if response.verdict.upper() in ("BLOCK", "REQUIRE_REVIEW", "REVIEW"):
        background_tasks.add_task(
            dispatch_decision_event,
            req=req,
            decision=response,
            organization_id=req.organization_id,
        )

    # Queue Human-in-the-Loop escalation for human oversight under EU AI Act Article 14
    if response.verdict.upper() in ("REQUIRE_REVIEW", "REVIEW"):
        audit_id_str = response.audit_token[:16] if response.audit_token else f"audit-{uuid.uuid4().hex[:8]}"
        background_tasks.add_task(
            record_hitl_escalation_if_needed,
            req=req,
            decision=response,
            organization_id=req.organization_id,
            audit_id=audit_id_str,
        )

    return response


@router.get("/stream", response_model=list[DecisionStreamItemResponse])
async def get_decision_stream(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the real-time stream of recent agent decisions evaluated by the gateway."""
    stmt = (
        select(DecisionEvaluation)
        .where(DecisionEvaluation.organization_id == organization_id)
        .order_by(DecisionEvaluation.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        DecisionStreamItemResponse(
            id=r.id,
            audit_id=r.audit_id,
            actor_id=r.actor_id,
            actor_role=r.actor_role,
            decision_prompt=r.decision_prompt,
            verdict=r.verdict,
            risk_level=r.risk_level,
            reasons=r.reasons or [],
            preferred_source=r.preferred_source,
            suggested_action=r.suggested_action,
            audit_token=r.audit_token,
            execution_ms=r.execution_ms,
            created_at=r.created_at,
        )
        for r in records
    ]
