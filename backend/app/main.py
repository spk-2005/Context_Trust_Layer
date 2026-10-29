from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.init_db import init_db_schema


from app.ingestion.scheduler import scheduler
from app.services.slack_worker import slack_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db_schema()
    except Exception as e:
        print(f"Warning: Failed to auto-initialize DB schema: {e}")
    scheduler.start()
    slack_worker.start()
    yield
    slack_worker.stop()
    scheduler.stop()


app = FastAPI(
    title=settings.app_name,
    description="Context Trust Layer - AI Agent Context Provenance, Validity, and Trust Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for deployed and local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "application": settings.app_name,
        "status": "running",
    }


@app.get("/health")
async def health():
    db_ok = False
    db_err = None
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            db_ok = result.scalar() == 1
    except Exception as e:
        db_err = str(e)

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": db_ok,
        "database_error": db_err,
        "database_configured": bool(settings.database_url and "localhost" not in settings.database_url),
        "app_env": settings.app_env,
    }


# Include API v1 router
app.include_router(api_v1_router)