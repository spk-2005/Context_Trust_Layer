from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.audit import router as audit_router
from app.api.v1.chat import router as chat_router
from app.api.v1.claims import router as claims_router
from app.api.v1.conflicts import router as conflicts_router
from app.api.v1.context import router as context_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.lineage import router as lineage_router
from app.api.v1.mcp import router as mcp_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.sources import router as sources_router
from app.api.v1.steward import router as steward_router
from app.api.v1.users import router as users_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.hitl import router as hitl_router
from app.api.v1.red_team import router as red_team_router
from app.api.v1.merkle import router as merkle_router
from app.api.v1.drift import router as drift_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(auth_router)

api_v1_router.include_router(health_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(claims_router)
api_v1_router.include_router(conflicts_router)
api_v1_router.include_router(context_router)
api_v1_router.include_router(decisions_router)
api_v1_router.include_router(lineage_router)
api_v1_router.include_router(steward_router)
api_v1_router.include_router(mcp_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(hitl_router)
api_v1_router.include_router(red_team_router)
api_v1_router.include_router(merkle_router)
api_v1_router.include_router(drift_router)



