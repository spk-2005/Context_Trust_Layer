import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.red_team import (
    CustomInjectRequest,
    CustomInjectResponse,
    RedTeamAttackCase,
    RedTeamRunRequest,
    RedTeamRunResponse,
)
from app.services.red_team_service import (
    BENCHMARK_ATTACK_CATALOG,
    execute_custom_injection,
    run_full_red_team_suite,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/red-team", tags=["red-team"])


@router.get("/catalog", response_model=List[RedTeamAttackCase])
async def get_attack_catalog():
    """Retrieve pre-configured adversarial benchmark attacks (OWASP Top 10 for LLMs)."""
    return BENCHMARK_ATTACK_CATALOG


@router.post("/run", response_model=RedTeamRunResponse)
async def run_red_team_benchmark(
    payload: RedTeamRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """Executes the automated adversarial benchmark test suite and calculates security robustness."""
    try:
        response = await run_full_red_team_suite(payload, db=db)
        return response
    except Exception as e:
        logger.error(f"Error running red team suite: {e}", exc_info=True)
        # Fallback without session if DB fails
        return await run_full_red_team_suite(payload, db=None)


@router.post("/inject", response_model=CustomInjectResponse)
async def inject_custom_attack(
    payload: CustomInjectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Test an ad-hoc custom adversarial prompt or jailbreak against the Decision Gate."""
    try:
        return await execute_custom_injection(payload, db=db)
    except Exception as e:
        logger.error(f"Error executing custom injection: {e}", exc_info=True)
        return await execute_custom_injection(payload, db=None)
