import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.data_source_repository import DataSourceRepository
from app.ingestion.sync_engine import SyncEngine, SyncResult
from app.schemas.data_source import DataSourceCreate, DataSourceResponse

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[DataSourceResponse])
async def list_data_sources(
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all configured data sources and live connector statuses for an organization."""
    repo = DataSourceRepository(db)
    sources = await repo.list_by_organization(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    return [DataSourceResponse.model_validate(s) for s in sources]


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new live data source connector (Confluence, Jira, GitHub, or Portal)."""
    repo = DataSourceRepository(db)
    source = await repo.get_or_create(
        organization_id=data.organization_id,
        name=data.name,
        source_type=data.source_type,
        external_id=data.external_id,
        authority_level=data.authority_level,
    )
    await db.commit()
    return DataSourceResponse.model_validate(source)


@router.post("/{source_id}/sync", response_model=SyncResult)
async def sync_single_source(
    source_id: uuid.UUID,
    use_mock_llm: bool = Query(True, description="Use fast deterministic rule-based LLM for extraction"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate live sync for a specific connector. Automatically extracts claims and detects conflicts."""
    sync_engine = SyncEngine(db)
    try:
        result = await sync_engine.sync_data_source(source_id=source_id, use_mock_llm=use_mock_llm)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}")


@router.post("/sync-all", response_model=list[SyncResult])
async def sync_all_sources(
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    use_mock_llm: bool = Query(True, description="Use fast deterministic rule-based LLM for extraction"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger synchronization across all registered connectors for an organization."""
    sync_engine = SyncEngine(db)
    try:
        results = await sync_engine.sync_all_organization_sources(
            organization_id=organization_id,
            use_mock_llm=use_mock_llm,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Bulk sync failed: {str(e)}")
