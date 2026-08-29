from fastapi import APIRouter

from app.api.v1.conflicts import router as conflicts_router
from app.api.v1.context import router as context_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(conflicts_router)
api_v1_router.include_router(context_router)
