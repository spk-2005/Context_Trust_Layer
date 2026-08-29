from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health(db: AsyncSession = Depends(get_db)):
    # Verify DB connectivity
    res = await db.execute(text("SELECT 1"))
    db_ok = res.scalar() == 1

    # Verify active extensions
    ext_res = await db.execute(text("SELECT extname FROM pg_extension"))
    extensions = [row[0] for row in ext_res.fetchall()]

    return HealthResponse(
        status="healthy" if db_ok else "unhealthy",
        database=db_ok,
        extensions=extensions,
    )
