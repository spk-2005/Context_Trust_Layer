from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.init_db import init_db_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db_schema()
    except Exception as e:
        print(f"Warning: Failed to auto-initialize DB schema: {e}")
    yield


app = FastAPI(
    title=settings.app_name,
    description="Context Trust Layer - AI Agent Context Provenance, Validity, and Trust Engine",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "application": settings.app_name,
        "status": "running",
    }


@app.get("/health")
async def health():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()

    return {
        "status": "healthy",
        "database": value == 1,
    }


# Include API v1 router
app.include_router(api_v1_router)