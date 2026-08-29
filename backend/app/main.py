from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.database import AsyncSessionLocal


app = FastAPI(
    title=settings.app_name,
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