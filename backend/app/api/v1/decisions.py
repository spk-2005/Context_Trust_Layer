from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.decision_engine.evaluator import DecisionEvaluator
from app.schemas.decision import (
    DecisionEvaluateRequest,
    DecisionEvaluateResponse,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/evaluate", response_model=DecisionEvaluateResponse)
async def evaluate_decision(
    req: DecisionEvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Evaluate an AI agent's intended decision and candidate evidence for validity, risk, and policy compliance."""
    evaluator = DecisionEvaluator(session=db)
    response = await evaluator.evaluate(req, session=db)
    return response
