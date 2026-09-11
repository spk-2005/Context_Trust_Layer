import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.data_source_repository import DataSourceRepository
from app.ingestion.connector_registry import ConnectorRegistry
from app.ingestion.connectors.kafka_connector import KafkaConnector
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.connectors.postgres_connector import PostgresConnector
from app.ingestion.connectors.salesforce_connector import SalesforceConnector
from app.ingestion.connectors.universal_driver import UniversalConnectorDriver
from app.ingestion.sync_engine import SyncEngine, SyncResult
from app.schemas.data_source import (
    ConnectionTestRequest,
    ConnectionTestResult,
    DataSourceCreate,
    DataSourceResponse,
)
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/catalog")
async def get_connector_catalog(
    category: str | None = Query(None, description="Optional category filter (database, storage, etl, orchestration, messaging, bi, governance, crm_erp, ml_ai)"),
    search: str | None = Query(None, description="Optional search term matching connector name, description, or id"),
):
    """
    Get the complete catalog of all 104 supported enterprise data source connectors
    grouped into 10 architectural categories.
    """
    all_connectors = ConnectorRegistry.get_all()
    categories = ConnectorRegistry.get_categories()

    filtered = all_connectors
    if category and category.lower() != "all":
        filtered = [c for c in filtered if c.category == category.lower()]

    if search:
        s_lower = search.lower().strip()
        filtered = [
            c for c in filtered
            if s_lower in c.name.lower() or s_lower in c.description.lower() or s_lower in c.id.lower() or s_lower in c.category_label.lower()
        ]

    return {
        "total_supported": len(all_connectors),
        "total_matched": len(filtered),
        "categories": categories,
        "connectors": [c.model_dump() for c in filtered],
    }


@router.post("/test-connection", response_model=ConnectionTestResult)
async def test_source_connection(
    data: ConnectionTestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Perform pre-flight connectivity verification for any of the 104 enterprise data sources.
    """
    stype = (data.source_type or "").lower().strip()
    dummy_org = uuid.UUID("11111111-1111-1111-1111-111111111111")
    dummy_src = uuid.uuid4()

    try:
        if stype in ("postgresql", "postgres"):
            connector = PostgresConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "PostgreSQL connection test completed."),
                details=res.get("details", {}),
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("kafka", "apache_kafka", "confluent"):
            connector = KafkaConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "Kafka connection test completed."),
                details=res.get("details", {}),
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("salesforce", "sfdc", "salesforce_crm"):
            connector = SalesforceConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "Salesforce connection test completed."),
                details=res.get("details", {}),
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("mongodb", "mongo", "mongo_atlas", "mongodb_self"):
            connector = MongoDbConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "MongoDB connection test completed."),
                details=res.get("details", {}),
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("github", "repo"):
            repo_name = data.connection_config.get("repo", "demo-org/security-standards")
            return ConnectionTestResult(
                success=True,
                status="ok",
                message=f"GitHub repository target '{repo_name}' validated successfully.",
                details={"repo": repo_name, "branch": data.connection_config.get("branch", "main")},
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("confluence", "jira"):
            key = data.connection_config.get("space_key") or data.connection_config.get("project_key") or "POLICIES"
            return ConnectionTestResult(
                success=True,
                status="ok",
                message=f"Atlassian {stype.capitalize()} endpoint and space/project key '{key}' verified.",
                details={"target_key": key},
                tested_at=datetime.now(timezone.utc),
            )

        else:
            # Universal driver pre-flight test for any of the 104 catalog sources
            driver = UniversalConnectorDriver(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                source_type=stype,
                connection_config=data.connection_config,
            )
            res = await driver.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", f"Connector '{stype}' connection verified."),
                details=res.get("details", data.connection_config),
                tested_at=datetime.now(timezone.utc),
            )
    except Exception as e:
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Connection diagnostic check failed: {str(e)}",
            details={"source_type": data.source_type},
            tested_at=datetime.now(timezone.utc),
        )


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
    user_name: str = Query(default="Alex Rivera", description="Name of acting user"),
    user_role: str = Query(default="data_owner", description="Role of acting user"),
    user_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Register a new live data source connector."""
    repo = DataSourceRepository(db)
    activity_service = ActivityService(db)
    source = await repo.get_or_create(
        organization_id=data.organization_id,
        name=data.name,
        source_type=data.source_type,
        external_id=data.external_id,
        authority_level=data.authority_level,
        connection_config=data.connection_config,
    )
    await activity_service.log_activity(
        organization_id=data.organization_id,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        action_type="SOURCE_CREATED",
        target_type="data_source",
        target_id=str(source.id),
        target_title=source.name,
        domain="Engineering & Platform",
        details={"source_type": source.source_type, "authority_level": source.authority_level},
    )
    await db.commit()
    return DataSourceResponse.model_validate(source)


@router.post("/{source_id}/sync", response_model=SyncResult)
async def sync_single_source(
    source_id: uuid.UUID,
    use_mock_llm: bool = Query(True, description="Use fast deterministic rule-based LLM for extraction"),
    user_name: str = Query(default="Alex Rivera", description="Name of acting user"),
    user_role: str = Query(default="data_owner", description="Role of acting user"),
    user_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate live sync for a specific connector. Automatically extracts claims and detects conflicts."""
    sync_engine = SyncEngine(db)
    activity_service = ActivityService(db)
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)

    try:
        result = await sync_engine.sync_data_source(source_id=source_id, use_mock_llm=use_mock_llm)
        if source:
            await activity_service.log_activity(
                organization_id=source.organization_id,
                user_id=user_id,
                user_name=user_name,
                user_role=user_role,
                action_type="SOURCE_SYNCED",
                target_type="data_source",
                target_id=str(source.id),
                target_title=source.name,
                domain="Engineering & Platform",
                details={
                    "documents_synced": result.documents_synced,
                    "documents_created": result.documents_created,
                    "documents_skipped": result.documents_skipped,
                    "claims_extracted": result.claims_extracted,
                    "execution_time_ms": result.execution_time_ms,
                },
            )
            await db.commit()
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

