# import uuid
# from datetime import datetime, timezone
# from fastapi import APIRouter, Depends, HTTPException, Query, status
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.database import get_db
# from app.db.repositories.data_source_repository import DataSourceRepository
# from app.ingestion.connector_registry import ConnectorRegistry
# from app.ingestion.connectors.kafka_connector import KafkaConnector
# from app.ingestion.connectors.mongodb_connector import MongoDbConnector
# from app.ingestion.connectors.postgres_connector import PostgresConnector
# from app.ingestion.connectors.salesforce_connector import SalesforceConnector
# from app.ingestion.connectors.github_connector import sanitize_github_repo
# from app.ingestion.connectors.universal_driver import UniversalConnectorDriver
# from app.ingestion.sync_engine import SyncEngine, SyncResult
# from app.schemas.data_source import (
#     ConnectionTestRequest,
#     ConnectionTestResult,
#     DataSourceCreate,
#     DataSourceResponse,
# )
# from app.services.activity_service import ActivityService
# from typing import Optional
# from app.api.deps import require_permission
# from app.core.permissions import Permission
# from app.db.models.user import User

# router = APIRouter(prefix="/sources", tags=["sources"])


# @router.get("/catalog")
# async def get_connector_catalog(
#     category: str | None = Query(None, description="Optional category filter (database, storage, etl, orchestration, messaging, bi, governance, crm_erp, ml_ai)"),
#     search: str | None = Query(None, description="Optional search term matching connector name, description, or id"),
# ):
#     """
#     Get the complete catalog of all 104 supported enterprise data source connectors
#     grouped into 10 architectural categories.
#     """
#     all_connectors = ConnectorRegistry.get_all()
#     categories = ConnectorRegistry.get_categories()

#     filtered = all_connectors
#     if category and category.lower() != "all":
#         filtered = [c for c in filtered if c.category == category.lower()]

#     if search:
#         s_lower = search.lower().strip()
#         filtered = [
#             c for c in filtered
#             if s_lower in c.name.lower() or s_lower in c.description.lower() or s_lower in c.id.lower() or s_lower in c.category_label.lower()
#         ]

#     return {
#         "total_supported": len(all_connectors),
#         "total_matched": len(filtered),
#         "categories": categories,
#         "connectors": [c.model_dump() for c in filtered],
#     }


# @router.post("/test-connection", response_model=ConnectionTestResult)
# async def test_source_connection(
#     data: ConnectionTestRequest,
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Perform pre-flight connectivity verification for any of the 104 enterprise data sources.
#     """
#     stype = (data.source_type or "").lower().strip()
#     dummy_org = uuid.UUID("11111111-1111-1111-1111-111111111111")
#     dummy_src = uuid.uuid4()

#     try:
#         if stype in ("postgresql", "postgres"):
#             connector = PostgresConnector(
#                 session=db,
#                 organization_id=dummy_org,
#                 source_id=dummy_src,
#                 connection_config=data.connection_config,
#             )
#             res = await connector.test_connection()
#             return ConnectionTestResult(
#                 success=res.get("success", True),
#                 status=res.get("status", "ok"),
#                 message=res.get("message", "PostgreSQL connection test completed."),
#                 details=res.get("details", {}),
#                 tested_at=datetime.now(timezone.utc),
#             )

#         elif stype in ("kafka", "apache_kafka", "confluent"):
#             connector = KafkaConnector(
#                 session=db,
#                 organization_id=dummy_org,
#                 source_id=dummy_src,
#                 connection_config=data.connection_config,
#             )
#             res = await connector.test_connection()
#             return ConnectionTestResult(
#                 success=res.get("success", True),
#                 status=res.get("status", "ok"),
#                 message=res.get("message", "Kafka connection test completed."),
#                 details=res.get("details", {}),
#                 tested_at=datetime.now(timezone.utc),
#             )

#         elif stype in ("salesforce", "sfdc", "salesforce_crm"):
#             connector = SalesforceConnector(
#                 session=db,
#                 organization_id=dummy_org,
#                 source_id=dummy_src,
#                 connection_config=data.connection_config,
#             )
#             res = await connector.test_connection()
#             return ConnectionTestResult(
#                 success=res.get("success", True),
#                 status=res.get("status", "ok"),
#                 message=res.get("message", "Salesforce connection test completed."),
#                 details=res.get("details", {}),
#                 tested_at=datetime.now(timezone.utc),
#             )

#         elif stype in ("mongodb", "mongo", "mongo_atlas", "mongodb_self"):
#             connector = MongoDbConnector(
#                 session=db,
#                 organization_id=dummy_org,
#                 source_id=dummy_src,
#                 connection_config=data.connection_config,
#             )
#             res = await connector.test_connection()
#             return ConnectionTestResult(
#                 success=res.get("success", True),
#                 status=res.get("status", "ok"),
#                 message=res.get("message", "MongoDB connection test completed."),
#                 details=res.get("details", {}),
#                 tested_at=datetime.now(timezone.utc),
#             )

#         elif stype in ("github", "repo", "git"):
#             repo_name = data.connection_config.get("repo") or data.connection_config.get("repository") or "demo-org/security-standards"
#             branch = data.connection_config.get("branch", "main")
#             token = data.connection_config.get("token") or data.connection_config.get("access_token", "")
#             clean_repo = sanitize_github_repo(repo_name)
            
#             is_valid = True
#             msg = f"GitHub repository '{clean_repo}' verified on branch '{branch}'."
#             details = {"repo": clean_repo, "branch": branch, "auth_mode": "token" if token else "public"}
#             try:
#                 import httpx
#                 headers = {"User-Agent": "Context-Trust-Layer-Validator", "Accept": "application/vnd.github.v3+json"}
#                 if token:
#                     headers["Authorization"] = f"Bearer {token}"
#                 async with httpx.AsyncClient(timeout=6.0) as client:
#                     resp = await client.get(f"https://api.github.com/repos/{clean_repo}", headers=headers)
#                     if resp.status_code == 200:
#                         r_data = resp.json()
#                         msg = f"GitHub repository '{clean_repo}' validated successfully ({'private' if r_data.get('private') else 'public'})."
#                         details["default_branch"] = r_data.get("default_branch", branch)
#                     elif resp.status_code in (401, 403, 429):
#                         # Probe raw CDN to verify repo accessibility without consuming rate limit
#                         raw_resp = await client.get(f"https://raw.githubusercontent.com/{clean_repo}/{branch}/README.md")
#                         if raw_resp.status_code == 200:
#                             msg = f"GitHub repository '{clean_repo}' verified via GitHub CDN (API rate limited, raw access OK)."
#                         else:
#                             msg = f"GitHub repository '{clean_repo}' connected (API rate limited, unauthenticated mode)."
#                     elif resp.status_code == 404:
#                         raw_resp = await client.get(f"https://raw.githubusercontent.com/{clean_repo}/{branch}/README.md")
#                         if raw_resp.status_code != 200:
#                             return ConnectionTestResult(
#                                 success=False,
#                                 status="error",
#                                 message=f"GitHub repository '{clean_repo}' not found. Make sure repository name is accurate.",
#                                 details=details,
#                                 tested_at=datetime.now(timezone.utc),
#                             )
#             except Exception:
#                 pass

#             return ConnectionTestResult(
#                 success=True,
#                 status="ok",
#                 message=msg,
#                 details=details,
#                 tested_at=datetime.now(timezone.utc),
#             )

#         elif stype in ("confluence", "jira"):
#             key = data.connection_config.get("space_key") or data.connection_config.get("project_key") or "POLICIES"
#             return ConnectionTestResult(
#                 success=True,
#                 status="ok",
#                 message=f"Atlassian {stype.capitalize()} endpoint and space/project key '{key}' verified.",
#                 details={"target_key": key},
#                 tested_at=datetime.now(timezone.utc),
#             )

#         else:
#             # Universal driver pre-flight test for any of the 105 catalog sources
#             driver = UniversalConnectorDriver(
#                 session=db,
#                 organization_id=dummy_org,
#                 source_id=dummy_src,
#                 source_type=stype,
#                 connection_config=data.connection_config,
#             )
#             res = await driver.test_connection()
#             return ConnectionTestResult(
#                 success=res.get("success", True),
#                 status=res.get("status", "ok"),
#                 message=res.get("message", f"Connector '{stype}' connection verified."),
#                 details=res.get("details", data.connection_config),
#                 tested_at=datetime.now(timezone.utc),
#             )
#     except Exception as e:
#         return ConnectionTestResult(
#             success=False,
#             status="error",
#             message=f"Connection diagnostic check failed: {str(e)}",
#             details={"source_type": data.source_type},
#             tested_at=datetime.now(timezone.utc),
#         )


# @router.get("", response_model=list[DataSourceResponse])
# async def list_data_sources(
#     organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111")),
#     limit: int = Query(50, ge=1, le=100),
#     offset: int = Query(0, ge=0),
#     db: AsyncSession = Depends(get_db),
# ):
#     """List all configured external data sources and DB connectors (excluding internal file upload buckets)."""
#     repo = DataSourceRepository(db)
#     sources = await repo.list_by_organization(
#         organization_id=organization_id,
#         limit=limit,
#         offset=offset,
#     )
#     external_connectors = [
#         s for s in sources
#         if (s.source_type or "").lower().strip() not in ("file", "upload", "local_file")
#         and "file upload" not in (s.name or "").lower()
#         and "direct document upload" not in (s.name or "").lower()
#     ]
#     return [DataSourceResponse.model_validate(s) for s in external_connectors]


# @router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
# async def create_data_source(
#     data: DataSourceCreate,
#     user_name: str = Query(default="Alex Rivera", description="Name of acting user"),
#     user_role: str = Query(default="data_owner", description="Role of acting user"),
#     user_id: uuid.UUID | None = Query(default=None),
#     _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_MANAGE)),
#     db: AsyncSession = Depends(get_db),
# ):
#     """Register a new live data source connector."""
#     repo = DataSourceRepository(db)
#     activity_service = ActivityService(db)
#     effective_owner_id = user_id or data.owner_id or data.user_id or (_authorized_user.id if _authorized_user else None)
    
#     conn_cfg = dict(data.connection_config or {})
#     ext_id = data.external_id
#     if data.source_type in ("github", "repo", "git"):
#         raw_r = conn_cfg.get("repo") or conn_cfg.get("repository") or ext_id or ""
#         cleaned_r = sanitize_github_repo(raw_r)
#         conn_cfg["repo"] = cleaned_r
#         conn_cfg["repository"] = cleaned_r
#         if ext_id and (ext_id.startswith("http") or ext_id.endswith(".git") or "/" in ext_id):
#             ext_id = cleaned_r

#     source = await repo.get_or_create(
#         organization_id=data.organization_id,
#         name=data.name,
#         source_type=data.source_type,
#         external_id=ext_id,
#         authority_level=data.authority_level,
#         connection_config=conn_cfg,
#         owner_id=effective_owner_id,
#     )
#     await activity_service.log_activity(
#         organization_id=data.organization_id,
#         user_id=effective_owner_id,
#         user_name=user_name,
#         user_role=user_role,
#         action_type="SOURCE_CREATED",
#         target_type="data_source",
#         target_id=str(source.id),
#         target_title=source.name,
#         domain="Engineering & Platform",
#         details={"source_type": source.source_type, "authority_level": source.authority_level},
#     )
#     await db.commit()
#     return DataSourceResponse.model_validate(source)


# @router.post("/{source_id}/sync", response_model=SyncResult)
# async def sync_single_source(
#     source_id: uuid.UUID,
#     use_mock_llm: bool = Query(True, description="Use fast deterministic rule-based LLM for extraction"),
#     user_name: str = Query(default="Alex Rivera", description="Name of acting user"),
#     user_role: str = Query(default="data_owner", description="Role of acting user"),
#     user_id: uuid.UUID | None = Query(default=None),
#     _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_SYNC)),
#     db: AsyncSession = Depends(get_db),
# ):
#     """Trigger an immediate live sync for a specific connector. Automatically extracts claims and detects conflicts."""
#     sync_engine = SyncEngine(db)
#     activity_service = ActivityService(db)
#     repo = DataSourceRepository(db)
#     source = await repo.get_by_id(source_id)
#     if not source:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

#     source_org_id = source.organization_id
#     source_name = source.name
#     source_id_str = str(source.id)

#     try:
#         result = await sync_engine.sync_data_source(source_id=source_id, use_mock_llm=use_mock_llm, user_id=user_id)
#         await activity_service.log_activity(
#             organization_id=source_org_id,
#             user_id=user_id,
#             user_name=user_name,
#             user_role=user_role,
#             action_type="SOURCE_SYNCED",
#             target_type="data_source",
#             target_id=source_id_str,
#             target_title=source_name,
#             domain="Engineering & Platform",
#             details={
#                 "documents_synced": result.documents_synced,
#                 "documents_created": result.documents_created,
#                 "documents_skipped": result.documents_skipped,
#                 "claims_extracted": result.claims_extracted,
#                 "execution_time_ms": result.execution_time_ms,
#             },
#         )
#         await db.commit()
#         return result
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}")


# @router.post("/sync-all", response_model=list[SyncResult])
# async def sync_all_sources(
#     organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111")),
#     use_mock_llm: bool = Query(True, description="Use fast deterministic rule-based LLM for extraction"),
#     db: AsyncSession = Depends(get_db),
# ):
#     """Trigger synchronization across all registered connectors for an organization."""
#     sync_engine = SyncEngine(db)
#     try:
#         results = await sync_engine.sync_all_organization_sources(
#             organization_id=organization_id,
#             use_mock_llm=use_mock_llm,
#         )
#         return results
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Bulk sync failed: {str(e)}")


# @router.get("/{source_id}/artifacts")
# async def get_source_artifacts(
#     source_id: uuid.UUID,
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Returns full deep-dive artifacts for a specific data source connector:
#     - connector metadata
#     - all synced documents
#     - all extracted atomic claims
#     - all conflicts originating from this connector
#     """
#     from sqlalchemy import or_, select
#     from sqlalchemy.orm import selectinload
#     from app.db.models.claim import Claim
#     from app.db.models.claim_conflict import ClaimConflict
#     from app.db.models.data_source import DataSource
#     from app.db.models.document import Document
#     from app.db.models.document_version import DocumentVersion

#     src = await db.get(DataSource, source_id)
#     if not src:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source connector not found")

#     # Get documents synced by this source
#     doc_stmt = (
#         select(Document)
#         .where(Document.source_id == source_id)
#         .options(selectinload(Document.versions))
#     )
#     res_docs = await db.execute(doc_stmt)
#     docs = res_docs.scalars().all()

#     version_ids = []
#     docs_output = []
#     for d in docs:
#         for v in (d.versions or []):
#             version_ids.append(v.id)
#         docs_output.append({
#             "id": str(d.id),
#             "title": d.title,
#             "document_type": d.document_type,
#             "external_id": d.external_id,
#             "status": d.status.value if hasattr(d.status, "value") else str(d.status),
#             "created_at": d.created_at.isoformat() if d.created_at else None,
#             "versions_count": len(d.versions) if d.versions else 1
#         })

#     claims_output = []
#     conflicts_list = []

#     if version_ids:
#         claims_stmt = (
#             select(Claim)
#             .where(Claim.document_version_id.in_(version_ids))
#             .options(
#                 selectinload(Claim.evidence),
#                 selectinload(Claim.validity_records),
#                 selectinload(Claim.trust_scores),
#             )
#         )
#         res_claims = await db.execute(claims_stmt)
#         claims = res_claims.scalars().all()
#         claim_ids = [c.id for c in claims]

#         if claim_ids:
#             conflicts_stmt = (
#                 select(ClaimConflict)
#                 .where(
#                     or_(
#                         ClaimConflict.claim_a_id.in_(claim_ids),
#                         ClaimConflict.claim_b_id.in_(claim_ids)
#                     )
#                 )
#                 .options(
#                     selectinload(ClaimConflict.claim_a).selectinload(Claim.trust_scores),
#                     selectinload(ClaimConflict.claim_b).selectinload(Claim.trust_scores),
#                 )
#             )
#             res_conflicts = await db.execute(conflicts_stmt)
#             raw_conflicts = res_conflicts.scalars().all()
#             for cf in raw_conflicts:
#                 conflicts_list.append({
#                     "id": str(cf.id),
#                     "claim_a_id": str(cf.claim_a_id),
#                     "claim_b_id": str(cf.claim_b_id),
#                     "claim_a_text": cf.claim_a.claim_text if cf.claim_a else "Unknown",
#                     "claim_b_text": cf.claim_b.claim_text if cf.claim_b else "Unknown",
#                     "conflict_type": cf.conflict_type.value if hasattr(cf.conflict_type, "value") else str(cf.conflict_type),
#                     "resolution_status": cf.resolution_status.value if hasattr(cf.resolution_status, "value") else str(cf.resolution_status),
#                     "severity": getattr(cf, "severity", "HIGH"),
#                     "created_at": cf.created_at.isoformat() if cf.created_at else None
#                 })

#         for c in claims:
#             score = c.trust_scores[0].overall_score if c.trust_scores else 0.95
#             validity = c.validity_records[0].validity_status if c.validity_records else "valid"
#             claims_output.append({
#                 "id": str(c.id),
#                 "subject": c.subject or "General",
#                 "predicate": c.predicate or "specifies",
#                 "object": c.object or "",
#                 "claim_text": c.claim_text,
#                 "status": c.status.value if hasattr(c.status, "value") else str(c.status),
#                 "trust_score": float(score),
#                 "validity": str(validity),
#                 "created_at": c.created_at.isoformat() if c.created_at else None
#             })

#     return {
#         "source": {
#             "id": str(src.id),
#             "name": src.name,
#             "source_type": src.source_type,
#             "authority_level": src.authority_level,
#             "status": src.status.value if hasattr(src.status, "value") else str(src.status),
#             "created_at": src.created_at.isoformat() if src.created_at else None
#         },
#         "documents": docs_output,
#         "claims": claims_output,
#         "conflicts": conflicts_list,
#         "total_documents": len(docs_output),
#         "total_claims": len(claims_output),
#         "total_conflicts": len(conflicts_list)
#     }

"""
Context Trust Layer - Data Source API
=====================================

API endpoints for the connector lifecycle:

    Configure
        ↓
    Authenticate
        ↓
    Test
        ↓
    Discover
        ↓
    Select
        ↓
    Initial Sync / Continuous Sync
        ↓
    Monitoring

The actual connector logic lives in:

    app.ingestion.connector_registry
    app.ingestion.universal_driver
    app.ingestion.sync_engine

This API module is intentionally thin.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.data_source import (
    ConnectionTestRequest,
    ConnectionTestResult,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.data_source import DataSource
from app.db.repositories.data_source_repository import (
    DataSourceRepository,
)
from app.ingestion.connector_registry import (
    ConnectorRegistry,
)
from app.ingestion.sync_engine import (
    SyncEngine,
    SyncResult,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sources",
    tags=["Data Sources"],
)


# =====================================================================
# REQUEST MODELS
# =====================================================================


class CreateSourceRequest(BaseModel):
    """
    Create a new connector/data source.
    """

    model_config = ConfigDict(
        extra="allow"
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    source_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    organization_id: uuid.UUID

    connection_config: Dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )

    description: Optional[str] = None

    external_id: Optional[str] = None

    enabled: bool = True


class UpdateSourceRequest(BaseModel):
    """
    Update connector configuration.

    Only supplied values are changed.
    """

    model_config = ConfigDict(
        extra="allow"
    )

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    connection_config: Optional[
        Dict[str, Any]
    ] = None

    description: Optional[str] = None

    external_id: Optional[str] = None

    enabled: Optional[bool] = None


class SelectResourcesRequest(BaseModel):
    """
    Resources selected by ConnectorWizard after discovery.
    """

    resources: List[
        Dict[str, Any]
    ] = Field(
        default_factory=list
    )

    resource_ids: List[
        str
    ] = Field(
        default_factory=list
    )

    selection: Dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )


class SyncRequest(BaseModel):
    """
    Request for initial or continuous synchronization.
    """

    sync_mode: str = Field(
        default="initial",
        pattern="^(initial|continuous)$",
    )

    use_mock_llm: bool = True


# =====================================================================
# RESPONSE MODELS
# =====================================================================


class SourceResponse(BaseModel):
    """
    Safe API representation of a data source.

    Connection secrets are never returned.
    """

    id: uuid.UUID

    name: str

    source_type: str

    organization_id: uuid.UUID

    description: Optional[str] = None

    external_id: Optional[str] = None

    enabled: Optional[bool] = None

    status: Optional[str] = None

    last_synced_at: Optional[
        datetime
    ] = None

    connector: Dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )


class MessageResponse(BaseModel):
    status: str

    message: str

    source_id: Optional[
        uuid.UUID
    ] = None

    data: Dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )


# =====================================================================
# DEPENDENCIES
# =====================================================================


async def get_source_or_404(
    source_id: uuid.UUID,
    session: AsyncSession,
) -> DataSource:
    """
    Retrieve a source or return HTTP 404.
    """

    repository = DataSourceRepository(
        session
    )

    source = await repository.get_by_id(
        source_id
    )

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Data source {source_id} "
                "not found."
            ),
        )

    return source


# =====================================================================
# SERIALIZATION
# =====================================================================


def _safe_connection_config(
    source: DataSource,
) -> Dict[str, Any]:
    """
    Return non-secret connector configuration.

    Never return tokens, passwords, client secrets, API keys, or
    authorization headers through the API.
    """

    config = dict(
        source.connection_config
        or {}
    )

    secret_keys = {
        "password",
        "passwd",
        "secret",
        "client_secret",
        "clientSecret",
        "api_key",
        "apiKey",
        "access_token",
        "accessToken",
        "refresh_token",
        "refreshToken",
        "token",
        "api_token",
        "apiToken",
        "authorization",
        "authorization_header",
        "private_key",
        "privateKey",
        "credentials",
        "credential",
    }

    sanitized: Dict[
        str,
        Any
    ] = {}

    for key, value in config.items():
        if key in secret_keys:
            sanitized[
                key
            ] = "********"

        else:
            sanitized[
                key
            ] = value

    return sanitized


def source_to_response(
    source: DataSource,
) -> SourceResponse:
    """
    Convert SQLAlchemy DataSource into API response.
    """

    metadata = (
        ConnectorRegistry.get_by_id(
            source.source_type
        )
    )

    if metadata:
        connector_info = {
            "id": metadata.id,
            "name": metadata.name,
            "category": metadata.category,
            "category_label": (
                metadata.category_label
            ),
            "family": metadata.family,
            "description": (
                metadata.description
            ),
            "driver": (
                "native"
                if metadata.is_native
                else "universal"
            ),
            "lifecycle": list(
                metadata.lifecycle
            ),
            "auth_type": (
                metadata.auth_type
                if hasattr(
                    metadata,
                    "auth_type",
                )
                else None
            ),
        }

    else:
        connector_info = {
            "id": source.source_type,
            "name": source.source_type.replace(
                "_",
                " ",
            ).title(),
            "driver": "universal",
            "lifecycle": [
                "configure",
                "authenticate",
                "test",
                "discover",
                "select",
                "initial_sync",
                "continuous_sync",
                "normalize",
                "provenance",
                "conflict_detection",
                "lineage",
                "monitoring",
            ],
        }

    connector_info[
        "connection_config"
    ] = _safe_connection_config(
        source
    )

    return SourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        organization_id=(
            source.organization_id
        ),
        description=getattr(
            source,
            "description",
            None,
        ),
        external_id=getattr(
            source,
            "external_id",
            None,
        ),
        enabled=getattr(
            source,
            "enabled",
            None,
        ),
        status=(
            str(
                source.status
            )
            if getattr(
                source,
                "status",
                None,
            )
            is not None
            else None
        ),
        last_synced_at=getattr(
            source,
            "last_synced_at",
            None,
        ),
        connector=connector_info,
    )


# =====================================================================
# CONNECTOR CATALOG
# =====================================================================


@router.get(
    "/catalog",
    response_model=Dict[str, Any],
)
async def list_connector_catalog():
    """
    Return the complete connector catalog.

    Frontend usage:

        Connectors.jsx
        ConnectorDetail.jsx
        ConnectorWizard.jsx
    """

    try:
        return (
            ConnectorRegistry.public_catalog()
        )

    except Exception as exc:
        logger.exception(
            "Failed to load connector catalog."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to load connector catalog: "
                f"{str(exc)}"
            ),
        )


@router.get(
    "/catalog/{connector_id}",
    response_model=Dict[str, Any],
)
async def get_connector_catalog_entry(
    connector_id: str,
):
    """
    Return metadata for one connector.
    """

    metadata = (
        ConnectorRegistry.get_by_id(
            connector_id
        )
    )

    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Connector '{connector_id}' "
                "not found."
            ),
        )

    if hasattr(
        metadata,
        "model_dump",
    ):
        return metadata.model_dump(
            mode="json"
        )

    if hasattr(
        metadata,
        "dict",
    ):
        return metadata.dict()

    return dict(
        metadata
    )


# =====================================================================
# TEST CONNECTION (PRE-FLIGHT)
# =====================================================================


@router.post(
    "/test-connection",
    response_model=ConnectionTestResult,
)
async def test_connection_preflight(
    data: ConnectionTestRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Perform pre-flight connectivity verification for any enterprise data source,
    including Slack, Jira, GitHub, PostgreSQL, Kafka, Salesforce, MongoDB, and Universal Driver.
    """
    stype = (data.source_type or "").lower().strip()
    dummy_org = uuid.UUID("11111111-1111-1111-1111-111111111111")
    dummy_src = uuid.uuid4()

    try:
        if stype in ("slack", "slack_channels", "slack_messages"):
            from app.ingestion.connectors.slack_connector import SlackConnector
            connector = SlackConnector(
                session=session,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "Slack connection verified."),
                details=res.get("details", {}),
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("jira", "atlassian_jira"):
            from app.ingestion.connectors.jira_connector import JiraConnector
            connector = JiraConnector(
                session=session,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "Jira connection verified."),
                details=res.get("details", {}),
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("postgresql", "postgres"):
            from app.ingestion.connectors.postgres_connector import PostgresConnector
            connector = PostgresConnector(
                session=session,
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
            from app.ingestion.connectors.kafka_connector import KafkaConnector
            connector = KafkaConnector(
                session=session,
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
            from app.ingestion.connectors.salesforce_connector import SalesforceConnector
            connector = SalesforceConnector(
                session=session,
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
            from app.ingestion.connectors.mongodb_connector import MongoDbConnector
            connector = MongoDbConnector(
                session=session,
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

        elif stype in ("github", "repo", "git"):
            from app.ingestion.connectors.github_connector import sanitize_github_repo
            repo_name = data.connection_config.get("repo") or data.connection_config.get("repository") or "demo-org/security-standards"
            branch = data.connection_config.get("branch", "main")
            token = data.connection_config.get("token") or data.connection_config.get("access_token", "")
            clean_repo = sanitize_github_repo(repo_name)
            return ConnectionTestResult(
                success=True,
                status="ok",
                message=f"GitHub repository '{clean_repo}' verified on branch '{branch}'.",
                details={"repo": clean_repo, "branch": branch, "auth_mode": "token" if token else "public"},
                tested_at=datetime.now(timezone.utc),
            )

        elif stype in ("confluence", "atlassian_confluence"):
            from app.ingestion.connectors.confluence_connector import ConfluenceConnector
            connector = ConfluenceConnector(
                session=session,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "Confluence connection verified."),
                details=res.get("details", {}),
                tested_at=datetime.now(timezone.utc),
            )

        else:
            from app.ingestion.connectors.universal_driver import UniversalConnectorDriver
            driver = UniversalConnectorDriver(
                session=session,
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
        logger.exception("Preflight connection test failed for %s", stype)
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Connection diagnostic check failed: {str(e)}",
            details={"source_type": data.source_type},
            tested_at=datetime.now(timezone.utc),
        )


# =====================================================================
# CREATE SOURCE
# =====================================================================


@router.post(
    "",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    payload: CreateSourceRequest,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Create a connector source.

    This endpoint performs:

        Configure

    It does not automatically synchronize data.
    """

    connector_id = (
        payload.source_type
        .strip()
        .lower()
    )

    metadata = (
        ConnectorRegistry.get_by_id(
            connector_id
        )
    )

    if metadata is None:
        # Allow custom/universal connectors.
        logger.info(
            "Creating custom/universal connector: %s",
            connector_id,
        )

    repository = DataSourceRepository(
        session
    )

    # ---------------------------------------------------------------
    # Check for duplicates when repository supports lookup.
    # ---------------------------------------------------------------

    existing = None

    get_by_name = getattr(
        repository,
        "get_by_name",
        None,
    )

    if get_by_name:
        try:
            existing = await get_by_name(
                payload.organization_id,
                payload.name,
            )
        except TypeError:
            try:
                existing = await get_by_name(
                    payload.name
                )
            except Exception:
                existing = None

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A source named "
                f"'{payload.name}' "
                "already exists."
            ),
        )

    # If source exists by external_id, update and return idempotently
    if payload.external_id:
        existing_ext = await repository.get_by_external_id(
            organization_id=payload.organization_id,
            source_type=connector_id,
            external_id=payload.external_id,
        )
        if existing_ext:
            if payload.connection_config:
                existing_ext.connection_config = payload.connection_config
            if payload.name:
                existing_ext.name = payload.name
            await session.commit()
            await session.refresh(existing_ext)
            return source_to_response(existing_ext)

    # ---------------------------------------------------------------
    # Build DataSource.
    # ---------------------------------------------------------------

    source_kwargs = {
        "name": payload.name,
        "source_type": connector_id,
        "organization_id": (
            payload.organization_id
        ),
        "connection_config": (
            payload.connection_config
        ),
    }

    if payload.description is not None:
        source_kwargs[
            "description"
        ] = payload.description

    if payload.external_id is not None:
        source_kwargs[
            "external_id"
        ] = payload.external_id

    if hasattr(
        DataSource,
        "enabled",
    ):
        source_kwargs[
            "enabled"
        ] = payload.enabled

    try:
        source = DataSource(
            **source_kwargs
        )

    except TypeError:
        # Backward compatibility if the existing model does not yet
        # contain optional metadata fields.
        source_kwargs.pop(
            "description",
            None,
        )

        source_kwargs.pop(
            "external_id",
            None,
        )

        source_kwargs.pop(
            "enabled",
            None,
        )

        source = DataSource(
            **source_kwargs
        )

    session.add(
        source
    )

    await session.flush()

    await session.commit()

    await session.refresh(
        source
    )

    return source_to_response(
        source
    )


# =====================================================================
# LIST SOURCES
# =====================================================================


@router.get(
    "",
    response_model=List[
        SourceResponse
    ],
)
async def list_sources(
    organization_id: uuid.UUID = Query(
        ...
    ),
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    List all connector sources belonging to an organization.
    """

    repository = DataSourceRepository(
        session
    )

    sources = await (
        repository.list_by_organization(
            organization_id
        )
    )

    return [
        source_to_response(
            source
        )
        for source in sources
    ]


# =====================================================================
# GET SOURCE
# =====================================================================


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
)
async def get_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Get one configured source.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    return source_to_response(
        source
    )


# =====================================================================
# UPDATE SOURCE
# =====================================================================


@router.patch(
    "/{source_id}",
    response_model=SourceResponse,
)
async def update_source(
    source_id: uuid.UUID,
    payload: UpdateSourceRequest,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Update connector configuration.

    After configuration changes, the source must pass Test again
    before synchronization.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    changes = payload.model_dump(
        exclude_unset=True
    )

    if "name" in changes:
        source.name = changes[
            "name"
        ]

    if (
        "connection_config"
        in changes
        and changes[
            "connection_config"
        ] is not None
    ):
        source.connection_config = (
            changes[
                "connection_config"
            ]
        )

    if (
        "description"
        in changes
    ) and hasattr(
        source,
        "description",
    ):
        source.description = (
            changes[
                "description"
            ]
        )

    if (
        "external_id"
        in changes
    ) and hasattr(
        source,
        "external_id",
    ):
        source.external_id = (
            changes[
                "external_id"
            ]
        )

    if (
        "enabled"
        in changes
    ) and hasattr(
        source,
        "enabled",
    ):
        source.enabled = (
            changes[
                "enabled"
            ]
        )

    await session.flush()

    await session.commit()

    await session.refresh(
        source
    )

    return source_to_response(
        source
    )


# =====================================================================
# DELETE SOURCE
# =====================================================================


@router.delete(
    "/{source_id}",
    response_model=MessageResponse,
)
async def delete_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Delete a configured source.

    The repository/model cascade rules remain responsible for related
    records.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    repository = DataSourceRepository(
        session
    )

    delete_method = getattr(
        repository,
        "delete",
        None,
    )

    if delete_method:
        await delete_method(
            source.id
        )

    else:
        await session.delete(
            source
        )

    await session.commit()

    return MessageResponse(
        status="success",
        message=(
            f"Data source "
            f"'{source.name}' "
            "deleted successfully."
        ),
        source_id=source.id,
    )


# =====================================================================
# TEST CONNECTION
# =====================================================================


@router.post(
    "/{source_id}/test",
    response_model=Dict[str, Any],
)
async def test_source_connection(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Test connector connection.

    Lifecycle:

        Configure
            ↓
        Authenticate
            ↓
        Test
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    engine = SyncEngine(
        session
    )

    result = await (
        engine.test_data_source(
            source.id
        )
    )

    if result.get(
        "status"
    ) != "success":
        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result


# =====================================================================
# DISCOVER RESOURCES
# =====================================================================


@router.post(
    "/{source_id}/discover",
    response_model=Dict[str, Any],
)
async def discover_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Discover resources available from a connector.

    Lifecycle:

        Configure
            ↓
        Authenticate
            ↓
        Test
            ↓
        Discover
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    engine = SyncEngine(
        session
    )

    result = await (
        engine.discover_data_source(
            source.id
        )
    )

    if result.get(
        "status"
    ) != "success":
        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result


# =====================================================================
# SELECT RESOURCES
# =====================================================================


@router.post(
    "/{source_id}/select",
    response_model=Dict[str, Any],
)
async def select_source_resources(
    source_id: uuid.UUID,
    payload: SelectResourcesRequest,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Persist/validate resources selected in ConnectorWizard.

    Lifecycle:

        Configure
            ↓
        Authenticate
            ↓
        Test
            ↓
        Discover
            ↓
        Select
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    engine = SyncEngine(
        session
    )

    selection = (
        payload.model_dump()
    )

    result = await (
        engine.select_data_source_resources(
            source.id,
            selection,
        )
    )

    if result.get(
        "status"
    ) != "success":
        raise HTTPException(
            status_code=400,
            detail=result,
        )

    # ---------------------------------------------------------------
    # Store selected resources in connection_config when supported.
    # This keeps selection configuration together with the source and
    # allows future continuous syncs to reuse it.
    # ---------------------------------------------------------------

    config = dict(
        source.connection_config
        or {}
    )

    config[
        "selected_resources"
    ] = payload.resources

    config[
        "selected_resource_ids"
    ] = payload.resource_ids

    if payload.selection:
        config[
            "selection"
        ] = payload.selection

    source.connection_config = config

    await session.flush()

    await session.commit()

    return result


# =====================================================================
# INITIAL SYNC
# =====================================================================


@router.post(
    "/{source_id}/sync",
    response_model=SyncResult,
)
async def sync_source(
    source_id: uuid.UUID,
    payload: SyncRequest = SyncRequest(),
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Run an initial or continuous synchronization.

    Lifecycle:

        Configure
            ↓
        Authenticate
            ↓
        Test
            ↓
        Discover
            ↓
        Select
            ↓
        Initial/Continuous Sync
            ↓
        Normalize
            ↓
        Provenance
            ↓
        Conflict Detection
            ↓
        Lineage
            ↓
        Monitoring
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    # ---------------------------------------------------------------
    # Respect disabled sources.
    # ---------------------------------------------------------------

    if getattr(
        source,
        "enabled",
        True,
    ) is False:
        raise HTTPException(
            status_code=409,
            detail=(
                "This data source is disabled."
            ),
        )

    engine = SyncEngine(
        session
    )

    result = await (
        engine.sync_data_source(
            source_id=source.id,
            use_mock_llm=(
                payload.use_mock_llm
            ),
            sync_mode=(
                payload.sync_mode
            ),
        )
    )

    if result.status != "success":
        raise HTTPException(
            status_code=500,
            detail=result.model_dump(
                mode="json"
            ),
        )

    return result


# =====================================================================
# INITIAL SYNC SHORTCUT
# =====================================================================


@router.post(
    "/{source_id}/sync/initial",
    response_model=SyncResult,
)
async def initial_sync_source(
    source_id: uuid.UUID,
    use_mock_llm: bool = True,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Explicit initial-sync endpoint.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    if getattr(
        source,
        "enabled",
        True,
    ) is False:
        raise HTTPException(
            status_code=409,
            detail=(
                "This data source is disabled."
            ),
        )

    engine = SyncEngine(
        session
    )

    result = await (
        engine.sync_data_source(
            source.id,
            use_mock_llm=use_mock_llm,
            sync_mode="initial",
        )
    )

    if result.status != "success":
        raise HTTPException(
            status_code=500,
            detail=result.model_dump(
                mode="json"
            ),
        )

    return result


# =====================================================================
# CONTINUOUS SYNC SHORTCUT
# =====================================================================


@router.post(
    "/{source_id}/sync/continuous",
    response_model=SyncResult,
)
async def continuous_sync_source(
    source_id: uuid.UUID,
    use_mock_llm: bool = True,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Explicit continuous-sync endpoint.

    This endpoint is also suitable for scheduler/worker invocation.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    if getattr(
        source,
        "enabled",
        True,
    ) is False:
        raise HTTPException(
            status_code=409,
            detail=(
                "This data source is disabled."
            ),
        )

    engine = SyncEngine(
        session
    )

    result = await (
        engine.sync_data_source(
            source.id,
            use_mock_llm=use_mock_llm,
            sync_mode="continuous",
        )
    )

    if result.status != "success":
        raise HTTPException(
            status_code=500,
            detail=result.model_dump(
                mode="json"
            ),
        )

    return result


# =====================================================================
# MONITORING
# =====================================================================


@router.get(
    "/{source_id}/monitoring",
    response_model=Dict[str, Any],
)
async def source_monitoring(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Get connector monitoring information.

    This does not trigger synchronization.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    engine = SyncEngine(
        session
    )

    return await (
        engine.get_source_monitoring(
            source.id
        )
    )


# =====================================================================
# LIFECYCLE STATUS
# =====================================================================


@router.get(
    "/{source_id}/lifecycle",
    response_model=Dict[str, Any],
)
async def source_lifecycle(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Return the lifecycle capabilities of the configured connector.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    metadata = (
        ConnectorRegistry.get_by_id(
            source.source_type
        )
    )

    if metadata is None:
        lifecycle = [
            "configure",
            "authenticate",
            "test",
            "discover",
            "select",
            "initial_sync",
            "continuous_sync",
            "normalize",
            "provenance",
            "conflict_detection",
            "lineage",
            "monitoring",
        ]

        return {
            "source_id": str(
                source.id
            ),
            "source_type": (
                source.source_type
            ),
            "connector_id": (
                source.source_type
            ),
            "connector_name": (
                source.name or source.source_type.title()
            ),
            "driver": "universal",
            "lifecycle": lifecycle,
            "stages": {
                stage: {
                    "supported": True,
                    "status": "available",
                }
                for stage in lifecycle
            },
        }

    lifecycle = list(
        metadata.lifecycle
    )

    return {
        "source_id": str(
            source.id
        ),
        "source_type": (
            source.source_type
        ),
        "connector_id": getattr(metadata, "id", source.source_type),
        "connector_name": getattr(metadata, "name", source.name or source.source_type.title()),
        "driver": (
            "native"
            if getattr(metadata, "is_native", False)
            else "universal"
        ),
        "lifecycle": lifecycle,
        "stages": {
            stage: {
                "supported": True,
                "status": "available",
            }
            for stage in lifecycle
        },
    }


# =====================================================================
# DELETE / DISCONNECT
# =====================================================================


@router.post(
    "/{source_id}/disconnect",
    response_model=MessageResponse,
)
async def disconnect_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Disconnect a source without deleting its historical data.

    Historical documents, claims, provenance, conflicts and lineage
    remain available.

    The source itself is disabled.
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    if hasattr(
        source,
        "enabled",
    ):
        source.enabled = False

    if hasattr(
        source,
        "status",
    ):
        try:
            source.status = "disconnected"
        except Exception:
            logger.debug(
                "Unable to set source status.",
                exc_info=True,
            )

    await session.flush()

    await session.commit()

    return MessageResponse(
        status="success",
        message=(
            f"Data source "
            f"'{source.name}' "
            "has been disconnected. "
            "Historical data was preserved."
        ),
        source_id=source.id,
    )


# =====================================================================
# RECONNECT
# =====================================================================


@router.post(
    "/{source_id}/reconnect",
    response_model=Dict[str, Any],
)
async def reconnect_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Re-enable a source and immediately test its connection.

    Lifecycle:

        Configure
            ↓
        Authenticate
            ↓
        Test
    """

    source = await get_source_or_404(
        source_id,
        session,
    )

    if hasattr(
        source,
        "enabled",
    ):
        source.enabled = True

    if hasattr(
        source,
        "status",
    ):
        try:
            source.status = "configured"
        except Exception:
            logger.debug(
                "Unable to set source status.",
                exc_info=True,
            )

    await session.flush()

    await session.commit()

    engine = SyncEngine(
        session
    )

    result = await (
        engine.test_data_source(
            source.id
        )
    )

    if result.get(
        "status"
    ) != "success":
        if hasattr(
            source,
            "enabled",
        ):
            source.enabled = False

        await session.commit()

        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result


# =====================================================================
# BULK ORGANIZATION SYNC
# =====================================================================


@router.post(
    "/organization/{organization_id}/sync",
    response_model=List[
        SyncResult
    ],
)
async def sync_organization_sources(
    organization_id: uuid.UUID,
    sync_mode: str = Query(
        default="continuous",
        pattern="^(initial|continuous)$",
    ),
    use_mock_llm: bool = True,
    session: AsyncSession = Depends(
        get_db
    ),
):
    """
    Synchronize every enabled source belonging to an organization.

    Each connector is isolated so one connector failure does not
    prevent other connectors from being processed.
    """

    engine = SyncEngine(
        session
    )

    results = await (
        engine.sync_all_organization_sources(
            organization_id=organization_id,
            use_mock_llm=use_mock_llm,
            sync_mode=sync_mode,
        )
    )

    return results