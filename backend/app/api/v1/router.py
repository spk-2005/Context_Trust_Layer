from fastapi import APIRouter
from app.api.v1.audit import router as audit_router
from app.api.v1.claims import router as claims_router
from app.api.v1.conflicts import router as conflicts_router
from app.api.v1.context import router as context_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.mcp import router as mcp_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.sources import router as sources_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(claims_router)
api_v1_router.include_router(conflicts_router)
api_v1_router.include_router(context_router)
api_v1_router.include_router(decisions_router)
api_v1_router.include_router(mcp_router)
api_v1_router.include_router(audit_router)

