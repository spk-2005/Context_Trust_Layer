"""
Context Trust Layer - Connector Sync Engine
===========================================

Central orchestration layer for connector synchronization.

Connector lifecycle:

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
    Normalize
        ↓
    Provenance
        ↓
    Conflict Detection
        ↓
    Lineage
        ↓
    Monitoring

Important architectural rule:

    Connector implementations are responsible for communicating with
    their external source.

    SyncEngine is responsible for orchestrating the Context Trust Layer
    ingestion/trust pipeline.

Existing native connectors are preserved:

    PostgreSQL
    Kafka
    Salesforce
    MongoDB
    Confluence
    Jira
    GitHub

All other catalog connectors can use UniversalConnectorDriver.

The existing persistence pipeline is intentionally preserved:

    connector.sync()
        ↓
    document/version persistence
        ↓
    claim extraction
        ↓
    conflict detection
        ↓
    trust calculation
        ↓
    commit
"""

from __future__ import annotations

import inspect
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data_source import DataSource
from app.db.repositories.data_source_repository import (
    DataSourceRepository,
)
from app.ingestion.connector_registry import (
    CONNECTOR_LIFECYCLE,
    ConnectorMetadata,
    ConnectorRegistry,
)
from app.ingestion.connectors.confluence_connector import (
    ConfluenceConnector,
)
from app.ingestion.connectors.github_connector import (
    GitHubConnector,
    sanitize_github_repo,
)
from app.ingestion.connectors.jira_connector import (
    JiraConnector,
)
from app.ingestion.connectors.kafka_connector import (
    KafkaConnector,
)
from app.ingestion.connectors.mongodb_connector import (
    MongoDbConnector,
)
from app.ingestion.connectors.postgres_connector import (
    PostgresConnector,
)
from app.ingestion.connectors.salesforce_connector import (
    SalesforceConnector,
)
from app.ingestion.connectors.slack_connector import (
    SlackConnector,
)
from app.ingestion.connectors.universal_driver import (
    UniversalConnectorDriver,
)
from app.services.claim_extraction_service import (
    ClaimExtractionService,
)
from app.services.conflict_service import (
    ConflictService,
)
from app.services.trust_service import (
    TrustService,
)


logger = logging.getLogger(__name__)


# =====================================================================
# LIFECYCLE RESULT MODELS
# =====================================================================


class LifecycleStageResult(BaseModel):
    """
    Standard result for an individual connector lifecycle stage.
    """

    stage: str

    status: str = "success"

    success: bool = True

    message: Optional[str] = None

    started_at: Optional[datetime] = None

    completed_at: Optional[datetime] = None

    execution_time_ms: int = 0

    data: Dict[str, Any] = Field(
        default_factory=dict
    )

    error: Optional[str] = None


class SyncResult(BaseModel):
    """
    Existing synchronization result.

    Existing fields are preserved so existing API consumers do not
    break.
    """

    source_id: uuid.UUID

    source_name: str

    source_type: str

    documents_synced: int

    documents_created: int = 0

    documents_updated: int = 0

    documents_skipped: int = 0

    claims_extracted: int

    conflicts_detected: int

    execution_time_ms: int = 0

    status: str = "success"

    synced_at: datetime

    message: str

    # New lifecycle information.
    lifecycle: Dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )

    monitoring: Dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )


# =====================================================================
# SYNC ENGINE
# =====================================================================


class SyncEngine:
    """
    Orchestrates connector lifecycle and Context Trust ingestion.

    The class deliberately keeps the existing application services:

        ClaimExtractionService
        ConflictService
        TrustService

    rather than moving trust logic into individual connectors.
    """

    # ---------------------------------------------------------------
    # Native connector aliases
    # ---------------------------------------------------------------

    NATIVE_CONNECTOR_ALIASES = {
        "postgresql": "postgresql",
        "postgres": "postgresql",

        "kafka": "kafka",
        "apache_kafka": "kafka",
        "confluent": "kafka",

        "salesforce": "salesforce",
        "sfdc": "salesforce",
        "salesforce_crm": "salesforce",

        "mongodb": "mongodb",
        "mongo": "mongodb",
        "mongo_atlas": "mongodb",

        "confluence": "confluence",
        "wiki": "confluence",

        "jira": "jira",
        "jira_issues": "jira",

        "github": "github",
        "repo": "github",
        "git": "github",
    }

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session

        self.source_repo = (
            DataSourceRepository(
                session
            )
        )

        self.extraction_service = (
            ClaimExtractionService(
                session
            )
        )

        self.conflict_service = (
            ConflictService(
                session
            )
        )

        self.trust_service = (
            TrustService(
                session
            )
        )

    # =================================================================
    # SOURCE / CONNECTOR RESOLUTION
    # =================================================================

    def get_connector_metadata(
        self,
        source: DataSource,
    ) -> ConnectorMetadata:
        """
        Resolve catalog metadata for a DataSource.
        """

        source_type = (
            source.source_type
            or ""
        ).strip().lower()

        metadata = (
            ConnectorRegistry.get_by_id(
                source_type
            )
        )

        if metadata is not None:
            return metadata

        # Safe fallback for legacy/custom source types.
        return ConnectorMetadata(
            id=source_type
            or "custom",
            name=(
                source_type
                or "Custom Source"
            ).replace(
                "_",
                " ",
            ).title(),
            category="custom",
            category_label="Custom Source",
            family="enterprise_app",
            description=(
                f"Enterprise connector for "
                f"{source_type or 'custom'}"
            ),
            monitored_scope=(
                "Enterprise data and policy synchronization."
            ),
            driver="universal",
        )

    def get_connector_for_source(
        self,
        source: DataSource,
        owner_id: uuid.UUID | None = None,
    ):
        """
        Return the correct connector implementation for a DataSource.

        Native connectors are selected explicitly.

        Everything else is delegated to UniversalConnectorDriver.
        """

        source_type = (
            source.source_type
            or ""
        ).lower().strip()

        config = (
            source.connection_config
            or {}
        )

        effective_owner = (
            owner_id
            or source.owner_id
        )

        metadata = (
            self.get_connector_metadata(
                source
            )
        )

        # -------------------------------------------------------------
        # PostgreSQL
        # -------------------------------------------------------------

        if source_type in (
            "postgresql",
            "postgres",
        ):
            return PostgresConnector(
                session=self.session,
                organization_id=(
                    source.organization_id
                ),
                source_id=source.id,
                connection_config=config,
                owner_id=effective_owner,
            )

        # -------------------------------------------------------------
        # Kafka
        # -------------------------------------------------------------

        if source_type in (
            "kafka",
            "apache_kafka",
            "confluent",
        ):
            return KafkaConnector(
                session=self.session,
                organization_id=(
                    source.organization_id
                ),
                source_id=source.id,
                connection_config=config,
                owner_id=effective_owner,
            )

        # -------------------------------------------------------------
        # Salesforce
        # -------------------------------------------------------------

        if source_type in (
            "salesforce",
            "sfdc",
            "salesforce_crm",
        ):
            return SalesforceConnector(
                session=self.session,
                organization_id=(
                    source.organization_id
                ),
                source_id=source.id,
                connection_config=config,
                owner_id=effective_owner,
            )

        # -------------------------------------------------------------
        # MongoDB
        # -------------------------------------------------------------

        if source_type in (
            "mongodb",
            "mongo",
            "mongo_atlas",
        ):
            return MongoDbConnector(
                session=self.session,
                organization_id=(
                    source.organization_id
                ),
                source_id=source.id,
                connection_config=config,
                owner_id=effective_owner,
            )

        # -------------------------------------------------------------
        # Confluence
        # -------------------------------------------------------------

        if source_type in (
            "confluence",
            "wiki",
        ):
            return ConfluenceConnector(
                session=self.session,
                organization_id=(
                    source.organization_id
                ),
                source_id=source.id,
                space_key=(
                    config.get(
                        "space_key"
                    )
                    or source.external_id
                    or "POLICIES"
                ),
                base_url=(
                    config.get(
                        "base_url"
                    )
                    or config.get(
                        "url"
                    )
                    or config.get(
                        "confluenceBaseUrl"
                    )
                ),
                api_token=(
                    config.get(
                        "api_token"
                    )
                    or config.get(
                        "token"
                    )
                    or config.get(
                        "confluenceToken"
                    )
                ),
                user_email=(
                    config.get(
                        "user_email"
                    )
                    or config.get(
                        "email"
                    )
                ),
                owner_id=effective_owner,
            )

        # -------------------------------------------------------------
        # Jira
        # -------------------------------------------------------------

        if source_type in (
            "jira",
            "jira_issues",
        ):
            return JiraConnector(
                session=self.session,
                organization_id=(
                    source.organization_id
                ),
                source_id=source.id,
                project_key=(
                    config.get(
                        "project_key"
                    )
                    or source.external_id
                    or "OPS"
                ),
                base_url=(
                    config.get(
                        "base_url"
                    )
                    or config.get(
                        "url"
                    )
                    or config.get(
                        "jiraBaseUrl"
                    )
                ),
                api_token=(
                    config.get(
                        "api_token"
                    )
                    or config.get(
                        "token"
                    )
                    or config.get(
                        "jiraToken"
                    )
                ),
                user_email=(
                    config.get(
                        "user_email"
                    )
                    or config.get(
                        "email"
                    )
                ),
                owner_id=effective_owner,
            )

        # -------------------------------------------------------------
        # Slack
        # -------------------------------------------------------------

        if source_type in (
            "slack",
            "slack_channels",
            "slack_messages",
        ):
            return SlackConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                bot_token=(
                    config.get("bot_token")
                    or config.get("token")
                    or config.get("api_token")
                ),
                channels=(
                    config.get("channels")
                    or config.get("channel_ids")
                    or config.get("channel")
                    or "secops-incidents,billing-compliance"
                ),
                workspace_name=(
                    config.get("workspace_name")
                    or config.get("workspace")
                    or "Enterprise-HQ"
                ),
                owner_id=effective_owner,
                connection_config=config,
            )

        # -------------------------------------------------------------
        # GitHub
        # -------------------------------------------------------------

        if source_type in (
            "github",
            "repo",
            "git",
        ):
            raw_repo = (
                config.get(
                    "repository"
                )
                or config.get(
                    "repo"
                )
                or source.external_id
                or "demo-org/security-standards"
            )

            repo_target = (
                sanitize_github_repo(
                    raw_repo
                )
            )

            token_val = (
                config.get(
                    "access_token"
                )
                or config.get(
                    "token"
                )
            )

            return GitHubConnector(
                session=self.session,
                organization_id=(
                    source.organization_id
                ),
                source_id=source.id,
                repo=repo_target,
                branch=config.get(
                    "branch"
                ),
                token=token_val,
                owner_id=effective_owner,
            )

        # -------------------------------------------------------------
        # Universal driver
        # -------------------------------------------------------------

        return UniversalConnectorDriver(
            session=self.session,
            organization_id=(
                source.organization_id
            ),
            source_id=source.id,
            source_type=metadata.id,
            connection_config=config,
            connector_metadata=metadata,
            owner_id=effective_owner,
        )

    # =================================================================
    # GENERIC METHOD INVOCATION
    # =================================================================

    async def _call_stage(
        self,
        connector: Any,
        stage: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Invoke a connector lifecycle method.

        The method supports connectors implementing:

            configure()
            authenticate()
            test()
            discover()
            select()
            initial_sync()
            continuous_sync()
            normalize()
            provenance()
            conflict_detection()
            lineage()
            monitoring()

        Backward-compatible connectors that only implement sync() are
        also supported.
        """

        method = getattr(
            connector,
            stage,
            None,
        )

        if method is None:
            raise NotImplementedError(
                f"Connector {type(connector).__name__} "
                f"does not implement lifecycle stage '{stage}'."
            )

        result = method(
            *args,
            **kwargs,
        )

        if inspect.isawaitable(
            result
        ):
            result = await result

        return result

    async def _run_stage(
        self,
        connector: Any,
        stage: str,
        *,
        args: Optional[
            Sequence[Any]
        ] = None,
        kwargs: Optional[
            Dict[str, Any]
        ] = None,
    ) -> LifecycleStageResult:
        """
        Execute one lifecycle stage and record timing/status.
        """

        started_at = datetime.now(
            timezone.utc
        )

        start = time.perf_counter()

        try:
            result = await self._call_stage(
                connector,
                stage,
                *(args or []),
                **(kwargs or {}),
            )

            elapsed = max(
                1,
                int(
                    (
                        time.perf_counter()
                        - start
                    )
                    * 1000
                ),
            )

            completed_at = (
                datetime.now(
                    timezone.utc
                )
            )

            # ---------------------------------------------------------
            # Standardize dictionary results.
            # ---------------------------------------------------------

            if isinstance(
                result,
                dict,
            ):
                success = result.get(
                    "success",
                    True,
                )

                status = result.get(
                    "status",
                    "success"
                    if success
                    else "error",
                )

                message = result.get(
                    "message"
                )

                data = dict(
                    result
                )

                # Avoid duplicating the standard fields.
                data.pop(
                    "success",
                    None,
                )
                data.pop(
                    "status",
                    None,
                )
                data.pop(
                    "message",
                    None,
                )

            else:
                success = True
                status = "success"
                message = None
                data = {
                    "result": result
                }

            return LifecycleStageResult(
                stage=stage,
                status=status,
                success=bool(
                    success
                ),
                message=message,
                started_at=started_at,
                completed_at=completed_at,
                execution_time_ms=elapsed,
                data=data,
            )

        except NotImplementedError as exc:
            elapsed = max(
                1,
                int(
                    (
                        time.perf_counter()
                        - start
                    )
                    * 1000
                ),
            )

            return LifecycleStageResult(
                stage=stage,
                status="not_implemented",
                success=False,
                message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(
                    timezone.utc
                ),
                execution_time_ms=elapsed,
                error=str(exc),
            )

        except Exception as exc:
            elapsed = max(
                1,
                int(
                    (
                        time.perf_counter()
                        - start
                    )
                    * 1000
                ),
            )

            logger.exception(
                "Connector lifecycle stage '%s' failed.",
                stage,
            )

            return LifecycleStageResult(
                stage=stage,
                status="error",
                success=False,
                message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(
                    timezone.utc
                ),
                execution_time_ms=elapsed,
                error=str(exc),
            )

    # =================================================================
    # LIFECYCLE EXECUTION
    # =================================================================

    async def run_connector_lifecycle(
        self,
        source: DataSource,
        *,
        owner_id: uuid.UUID | None = None,
        selection: Optional[
            Dict[str, Any]
        ] = None,
        sync_mode: str = "initial",
        execute_sync: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the connector lifecycle up to synchronization.

        This method is useful for:

            - connection testing
            - connector wizard
            - discovery
            - selection
            - lifecycle monitoring

        It does not replace sync_data_source(). The latter additionally
        runs the existing document/claim/conflict/trust pipeline.
        """

        connector = (
            self.get_connector_for_source(
                source,
                owner_id=owner_id,
            )
        )

        metadata = (
            self.get_connector_metadata(
                source
            )
        )

        lifecycle: Dict[
            str,
            Any
        ] = {}

        result: Dict[
            str,
            Any
        ] = {
            "source_id": str(
                source.id
            ),
            "source_name": source.name,
            "source_type": source.source_type,
            "connector_id": metadata.id,
            "connector_name": metadata.name,
            "driver": (
                "native"
                if metadata.is_native
                else "universal"
            ),
            "status": "started",
            "lifecycle": lifecycle,
            "started_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        # -------------------------------------------------------------
        # Stage 1 - Configure
        # -------------------------------------------------------------

        configure = await self._run_stage(
            connector,
            "configure",
        )

        lifecycle[
            "configure"
        ] = configure.model_dump(
            mode="json"
        )

        if not configure.success:
            return self._finish_lifecycle(
                result,
                status=configure.status,
                error=configure.error
                or configure.message,
            )

        # -------------------------------------------------------------
        # Stage 2 - Authenticate
        # -------------------------------------------------------------

        authenticate = await self._run_stage(
            connector,
            "authenticate",
        )

        lifecycle[
            "authenticate"
        ] = authenticate.model_dump(
            mode="json"
        )

        if not authenticate.success:
            return self._finish_lifecycle(
                result,
                status=authenticate.status,
                error=authenticate.error
                or authenticate.message,
            )

        # -------------------------------------------------------------
        # Stage 3 - Test
        # -------------------------------------------------------------

        test = await self._run_stage(
            connector,
            "test",
        )

        lifecycle[
            "test"
        ] = test.model_dump(
            mode="json"
        )

        if not test.success:
            return self._finish_lifecycle(
                result,
                status=test.status,
                error=test.error
                or test.message,
            )

        # -------------------------------------------------------------
        # Stage 4 - Discover
        # -------------------------------------------------------------

        discover = await self._run_stage(
            connector,
            "discover",
        )

        lifecycle[
            "discover"
        ] = discover.model_dump(
            mode="json"
        )

        if not discover.success:
            return self._finish_lifecycle(
                result,
                status=discover.status,
                error=discover.error
                or discover.message,
            )

        # -------------------------------------------------------------
        # Stage 5 - Select
        # -------------------------------------------------------------

        if selection is None:
            discovered_resources = (
                discover.data.get(
                    "resources",
                    [],
                )
            )

            selection = {
                "resources": (
                    discovered_resources
                )
            }

        select = await self._run_stage(
            connector,
            "select",
            args=[
                selection
            ],
        )

        lifecycle[
            "select"
        ] = select.model_dump(
            mode="json"
        )

        if not select.success:
            return self._finish_lifecycle(
                result,
                status=select.status,
                error=select.error
                or select.message,
            )

        # -------------------------------------------------------------
        # Stage 6 - Initial/Continuous Sync
        # -------------------------------------------------------------

        if execute_sync:
            sync_stage = (
                "continuous_sync"
                if sync_mode
                == "continuous"
                else "initial_sync"
            )

            sync = await self._run_stage(
                connector,
                sync_stage,
            )

            lifecycle[
                sync_stage
            ] = sync.model_dump(
                mode="json"
            )

            if not sync.success:
                return self._finish_lifecycle(
                    result,
                    status=sync.status,
                    error=sync.error
                    or sync.message,
                )

            records = self._extract_stage_records(
                sync
            )

            # ---------------------------------------------------------
            # Normalize
            # ---------------------------------------------------------

            normalize = await self._run_stage(
                connector,
                "normalize",
                args=[
                    records
                ],
            )

            lifecycle[
                "normalize"
            ] = normalize.model_dump(
                mode="json"
            )

            if not normalize.success:
                return self._finish_lifecycle(
                    result,
                    status=normalize.status,
                    error=normalize.error
                    or normalize.message,
                )

            records = (
                self._extract_stage_records(
                    normalize
                )
            )

            # ---------------------------------------------------------
            # Provenance
            # ---------------------------------------------------------

            provenance = await self._run_stage(
                connector,
                "provenance",
                args=[
                    records
                ],
            )

            lifecycle[
                "provenance"
            ] = provenance.model_dump(
                mode="json"
            )

            if not provenance.success:
                return self._finish_lifecycle(
                    result,
                    status=provenance.status,
                    error=provenance.error
                    or provenance.message,
                )

            records = (
                self._extract_stage_records(
                    provenance
                )
            )

            # ---------------------------------------------------------
            # Conflict Detection
            # ---------------------------------------------------------

            conflict_detection = (
                await self._run_stage(
                    connector,
                    "conflict_detection",
                    args=[
                        records
                    ],
                )
            )

            lifecycle[
                "conflict_detection"
            ] = (
                conflict_detection.model_dump(
                    mode="json"
                )
            )

            if not conflict_detection.success:
                return self._finish_lifecycle(
                    result,
                    status=(
                        conflict_detection.status
                    ),
                    error=(
                        conflict_detection.error
                        or conflict_detection.message
                    ),
                )

            records = (
                self._extract_stage_records(
                    conflict_detection
                )
            )

            # ---------------------------------------------------------
            # Lineage
            # ---------------------------------------------------------

            lineage = await self._run_stage(
                connector,
                "lineage",
                args=[
                    records
                ],
            )

            lifecycle[
                "lineage"
            ] = lineage.model_dump(
                mode="json"
            )

            if not lineage.success:
                return self._finish_lifecycle(
                    result,
                    status=lineage.status,
                    error=lineage.error
                    or lineage.message,
                )

            records = (
                self._extract_stage_records(
                    lineage
                )
            )

            result[
                "records"
            ] = records

            result[
                "records_count"
            ] = len(
                records
            )

        else:
            lifecycle[
                (
                    "continuous_sync"
                    if sync_mode
                    == "continuous"
                    else "initial_sync"
                )
            ] = {
                "stage": (
                    "continuous_sync"
                    if sync_mode
                    == "continuous"
                    else "initial_sync"
                ),
                "status": "skipped",
                "success": True,
                "message": (
                    "Synchronization was not executed."
                ),
            }

        # -------------------------------------------------------------
        # Monitoring
        # -------------------------------------------------------------

        monitoring = await self._run_stage(
            connector,
            "monitoring",
            kwargs={
                "status": "success",
                "records_processed": len(
                    result.get(
                        "records",
                        [],
                    )
                ),
            },
        )

        lifecycle[
            "monitoring"
        ] = monitoring.model_dump(
            mode="json"
        )

        return self._finish_lifecycle(
            result,
            status="success",
        )

    # =================================================================
    # COMPLETE TRUST PIPELINE
    # =================================================================

    async def sync_data_source(
        self,
        source_id: uuid.UUID,
        use_mock_llm: bool = True,
        user_id: uuid.UUID | None = None,
        sync_mode: str = "initial",
    ) -> SyncResult:
        """
        Execute a complete Context Trust Layer sync.

        This preserves the existing behavior:

            connector.sync()
                ↓
            document/version persistence
                ↓
            claim extraction
                ↓
            conflict detection
                ↓
            trust calculation
                ↓
            commit

        Lifecycle metadata is added around that pipeline.
        """

        start_time = (
            time.perf_counter()
        )

        source = await (
            self.source_repo.get_by_id(
                source_id
            )
        )

        if not source:
            raise ValueError(
                f"Data source {source_id} not found."
            )

        source_id_val = source.id

        source_name_val = (
            source.name
        )

        source_type_val = (
            source.source_type
        )

        effective_owner = (
            user_id
            or source.owner_id
        )

        if (
            user_id
            and not source.owner_id
        ):
            source.owner_id = user_id

        lifecycle_summary: Dict[
            str,
            Any
        ] = {}

        try:
            # ---------------------------------------------------------
            # Resolve connector
            # ---------------------------------------------------------

            connector = (
                self.get_connector_for_source(
                    source,
                    owner_id=effective_owner,
                )
            )

            metadata = (
                self.get_connector_metadata(
                    source
                )
            )

            lifecycle_summary[
                "connector"
            ] = {
                "id": metadata.id,
                "name": metadata.name,
                "driver": (
                    "native"
                    if metadata.is_native
                    else "universal"
                ),
            }

            # ---------------------------------------------------------
            # Configure
            # ---------------------------------------------------------

            configure = await self._run_stage(
                connector,
                "configure",
            )

            lifecycle_summary[
                "configure"
            ] = configure.model_dump(
                mode="json"
            )

            if not configure.success:
                raise RuntimeError(
                    configure.error
                    or configure.message
                    or "Connector configuration failed."
                )

            # ---------------------------------------------------------
            # Authenticate
            # ---------------------------------------------------------

            authenticate = await self._run_stage(
                connector,
                "authenticate",
            )

            lifecycle_summary[
                "authenticate"
            ] = authenticate.model_dump(
                mode="json"
            )

            if not authenticate.success:
                raise RuntimeError(
                    authenticate.error
                    or authenticate.message
                    or "Connector authentication failed."
                )

            # ---------------------------------------------------------
            # Test
            # ---------------------------------------------------------

            test = await self._run_stage(
                connector,
                "test",
            )

            lifecycle_summary[
                "test"
            ] = test.model_dump(
                mode="json"
            )

            if not test.success:
                logger.warning(
                    f"Connector connection test advisory for source {source.id}: "
                    f"{test.error or test.message}"
                )

            # ---------------------------------------------------------
            # Discover
            # ---------------------------------------------------------

            discover = await self._run_stage(
                connector,
                "discover",
            )

            lifecycle_summary[
                "discover"
            ] = discover.model_dump(
                mode="json"
            )

            if not discover.success:
                logger.warning(
                    f"Connector discovery advisory for source {source.id}: "
                    f"{discover.error or discover.message}"
                )

            # ---------------------------------------------------------
            # Select
            # ---------------------------------------------------------

            discovered_resources = (
                discover.data.get(
                    "resources",
                    [],
                ) if discover and discover.data else []
            )

            if not discovered_resources:
                discovered_resources = [
                    {
                        "id": str(source.id),
                        "name": source.name,
                        "type": source.source_type,
                        "selected": True,
                    }
                ]

            selection = {
                "resources": (
                    discovered_resources
                )
            }

            select = await self._run_stage(
                connector,
                "select",
                args=[
                    selection
                ],
            )

            lifecycle_summary[
                "select"
            ] = select.model_dump(
                mode="json"
            )

            if not select.success:
                raise RuntimeError(
                    select.error
                    or select.message
                    or "Connector selection failed."
                )

            # =========================================================
            # ACTUAL EXISTING SYNC PIPELINE
            # =========================================================

            # ---------------------------------------------------------
            # Initial/continuous source synchronization
            # ---------------------------------------------------------

            if sync_mode == "continuous":
                sync_method = getattr(
                    connector,
                    "continuous_sync",
                    None,
                )

                if sync_method is not None:
                    synced_docs = await sync_method()
                else:
                    synced_docs = await connector.sync()

                lifecycle_sync_stage = (
                    "continuous_sync"
                )

            else:
                sync_method = getattr(
                    connector,
                    "initial_sync",
                    None,
                )

                if sync_method is not None:
                    synced_docs = await sync_method()
                else:
                    synced_docs = await connector.sync()

                lifecycle_sync_stage = (
                    "initial_sync"
                )

            if synced_docs is None:
                synced_docs = []

            documents_synced_count = len(
                synced_docs
            )

            lifecycle_summary[
                lifecycle_sync_stage
            ] = {
                "stage": lifecycle_sync_stage,
                "success": True,
                "status": "success",
                "records_count": (
                    documents_synced_count
                ),
            }

            # ---------------------------------------------------------
            # Existing counters
            # ---------------------------------------------------------

            total_claims_extracted = 0

            total_conflicts_detected = 0

            documents_created_count = 0

            documents_updated_count = 0

            documents_skipped_count = 0

            # ---------------------------------------------------------
            # Fast rule-based provider for immediate responsive sync
            # ---------------------------------------------------------

            if use_mock_llm:
                from app.llm.mock_provider import (
                    MockLLMProvider,
                )

                llm_provider = (
                    MockLLMProvider()
                )

                extraction_service = (
                    ClaimExtractionService(
                        self.session,
                        llm_provider=llm_provider,
                    )
                )

                conflict_service = (
                    ConflictService(
                        self.session,
                        llm_provider=llm_provider,
                    )
                )

            else:
                extraction_service = (
                    self.extraction_service
                )

                conflict_service = (
                    self.conflict_service
                )

            # ---------------------------------------------------------
            # Process every synchronized document/version.
            # ---------------------------------------------------------

            for item in synced_docs:
                if len(item) == 3:
                    doc, version, is_changed = (
                        item
                    )

                else:
                    doc, version = (
                        item[0],
                        item[1],
                    )

                    # -------------------------------------------------
                    # Backward compatibility:
                    # Some existing connectors return only
                    # (document, version).
                    # -------------------------------------------------

                    from app.db.repositories.claim_repository import (
                        ClaimRepository,
                    )

                    claim_repo = (
                        ClaimRepository(
                            self.session
                        )
                    )

                    existing_claims = (
                        await claim_repo.list_by_version(
                            version.id
                        )
                    )

                    is_changed = (
                        len(
                            existing_claims
                        )
                        == 0
                    )

                # -----------------------------------------------------
                # Unchanged document
                # -----------------------------------------------------

                if not is_changed:
                    documents_skipped_count += 1

                    continue

                # -----------------------------------------------------
                # Created/updated document
                # -----------------------------------------------------

                if (
                    version.version_number
                    == 1
                ):
                    documents_created_count += 1

                else:
                    documents_updated_count += 1

                # -----------------------------------------------------
                # Normalize
                #
                # Existing connectors have already created the
                # application's Document/DocumentVersion objects.
                #
                # We retain the connector lifecycle boundary here
                # without replacing the existing persistence model.
                # -----------------------------------------------------

                lifecycle_summary.setdefault(
                    "normalize",
                    {
                        "stage": "normalize",
                        "success": True,
                        "status": "success",
                        "records_count": 0,
                    },
                )

                lifecycle_summary[
                    "normalize"
                ][
                    "records_count"
                ] += 1

                # -----------------------------------------------------
                # Provenance
                # -----------------------------------------------------

                lifecycle_summary.setdefault(
                    "provenance",
                    {
                        "stage": "provenance",
                        "success": True,
                        "status": "success",
                        "records_count": 0,
                    },
                )

                lifecycle_summary[
                    "provenance"
                ][
                    "records_count"
                ] += 1

                # -----------------------------------------------------
                # Claim extraction
                # -----------------------------------------------------

                claims = await (
                    extraction_service.extract_claims_from_version(
                        version.id
                    )
                )

                total_claims_extracted += (
                    len(
                        claims
                    )
                )

                # -----------------------------------------------------
                # Conflict detection
                # -----------------------------------------------------

                conflicts = await (
                    conflict_service.run_conflict_detection_for_version(
                        version.id
                    )
                )

                total_conflicts_detected += (
                    len(
                        conflicts
                    )
                )

                # -----------------------------------------------------
                # Trust calculation
                # -----------------------------------------------------

                await (
                    self.trust_service.calculate_for_version(
                        version.id
                    )
                )

                # -----------------------------------------------------
                # Lineage
                # -----------------------------------------------------

                lifecycle_summary.setdefault(
                    "lineage",
                    {
                        "stage": "lineage",
                        "success": True,
                        "status": "success",
                        "records_count": 0,
                    },
                )

                lifecycle_summary[
                    "lineage"
                ][
                    "records_count"
                ] += 1

                # -----------------------------------------------------
                # Conflict lifecycle boundary
                # -----------------------------------------------------

                lifecycle_summary.setdefault(
                    "conflict_detection",
                    {
                        "stage": "conflict_detection",
                        "success": True,
                        "status": "success",
                        "records_count": 0,
                    },
                )

                lifecycle_summary[
                    "conflict_detection"
                ][
                    "records_count"
                ] += len(
                    conflicts
                )

            # =========================================================
            # FINALIZE SOURCE
            # =========================================================

            synced_at_ts = (
                datetime.now(
                    timezone.utc
                )
            )

            source.last_synced_at = (
                synced_at_ts
            )

            await self.session.flush()

            await self.session.commit()

            # ---------------------------------------------------------
            # Monitoring
            # ---------------------------------------------------------

            exec_ms = max(
                1,
                int(
                    (
                        time.perf_counter()
                        - start_time
                    )
                    * 1000
                ),
            )

            lifecycle_summary[
                "monitoring"
            ] = {
                "stage": "monitoring",
                "success": True,
                "status": "success",
                "documents_synced": (
                    documents_synced_count
                ),
                "documents_created": (
                    documents_created_count
                ),
                "documents_updated": (
                    documents_updated_count
                ),
                "documents_skipped": (
                    documents_skipped_count
                ),
                "claims_extracted": (
                    total_claims_extracted
                ),
                "conflicts_detected": (
                    total_conflicts_detected
                ),
                "execution_time_ms": (
                    exec_ms
                ),
                "synced_at": (
                    synced_at_ts.isoformat()
                ),
            }

            # ---------------------------------------------------------
            # Message
            # ---------------------------------------------------------

            if (
                documents_skipped_count > 0
                and documents_created_count
                == 0
                and documents_updated_count
                == 0
            ):
                msg = (
                    f"⚡ Instant deduplication sync "
                    f"for {source_name_val}: "
                    f"{documents_skipped_count} documents "
                    f"verified unchanged "
                    f"(0 new claims extracted) "
                    f"in {exec_ms}ms."
                )

            else:
                msg = (
                    f"Successfully synced "
                    f"{documents_synced_count} documents "
                    f"({documents_created_count} new, "
                    f"{documents_updated_count} updated, "
                    f"{documents_skipped_count} unchanged) "
                    f"from {source_name_val}. "
                    f"Extracted "
                    f"{total_claims_extracted} atomic claims "
                    f"and surfaced "
                    f"{total_conflicts_detected} "
                    f"potential conflicts "
                    f"in {exec_ms}ms."
                )

            return SyncResult(
                source_id=source_id_val,
                source_name=source_name_val,
                source_type=source_type_val,
                documents_synced=(
                    documents_synced_count
                ),
                documents_created=(
                    documents_created_count
                ),
                documents_updated=(
                    documents_updated_count
                ),
                documents_skipped=(
                    documents_skipped_count
                ),
                claims_extracted=(
                    total_claims_extracted
                ),
                conflicts_detected=(
                    total_conflicts_detected
                ),
                execution_time_ms=exec_ms,
                status="success",
                synced_at=synced_at_ts,
                message=msg,
                lifecycle=lifecycle_summary,
                monitoring=(
                    lifecycle_summary.get(
                        "monitoring",
                        {},
                    )
                ),
            )

        except Exception as err:
            await self.session.rollback()

            exec_ms = max(
                1,
                int(
                    (
                        time.perf_counter()
                        - start_time
                    )
                    * 1000
                ),
            )

            logger.exception(
                "Sync failed for data source %s.",
                source_id,
            )

            lifecycle_summary[
                "monitoring"
            ] = {
                "stage": "monitoring",
                "success": False,
                "status": "error",
                "error": str(err),
                "execution_time_ms": (
                    exec_ms
                ),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            return SyncResult(
                source_id=source_id_val,
                source_name=source_name_val,
                source_type=source_type_val,
                documents_synced=0,
                documents_created=0,
                documents_updated=0,
                documents_skipped=0,
                claims_extracted=0,
                conflicts_detected=0,
                execution_time_ms=exec_ms,
                status="error",
                synced_at=datetime.now(
                    timezone.utc
                ),
                message=(
                    f"Sync failed for "
                    f"{source_name_val}: "
                    f"{str(err)}"
                ),
                lifecycle=lifecycle_summary,
                monitoring=(
                    lifecycle_summary.get(
                        "monitoring",
                        {},
                    )
                ),
            )

    # =================================================================
    # DISCOVERY-ONLY
    # =================================================================

    async def discover_data_source(
        self,
        source_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Dict[str, Any]:
        """
        Execute only:

            Configure
            Authenticate
            Test
            Discover

        Used by ConnectorWizard before the user selects resources.
        """

        source = await (
            self.source_repo.get_by_id(
                source_id
            )
        )

        if not source:
            raise ValueError(
                f"Data source {source_id} not found."
            )

        connector = (
            self.get_connector_for_source(
                source,
                owner_id=(
                    user_id
                    or source.owner_id
                ),
            )
        )

        result: Dict[
            str,
            Any
        ] = {
            "source_id": str(
                source.id
            ),
            "source_name": source.name,
            "source_type": source.source_type,
            "lifecycle": {},
        }

        for stage in (
            "configure",
            "authenticate",
            "test",
            "discover",
        ):
            stage_result = await (
                self._run_stage(
                    connector,
                    stage,
                )
            )

            result[
                "lifecycle"
            ][
                stage
            ] = stage_result.model_dump(
                mode="json"
            )

            if not stage_result.success:
                result[
                    "status"
                ] = stage_result.status

                result[
                    "message"
                ] = (
                    stage_result.error
                    or stage_result.message
                )

                return result

        result[
            "status"
        ] = "success"

        result[
            "resources"
        ] = result[
            "lifecycle"
        ][
            "discover"
        ].get(
            "data",
            {},
        ).get(
            "resources",
            [],
        )

        return result

    # =================================================================
    # SELECT RESOURCES
    # =================================================================

    async def select_data_source_resources(
        self,
        source_id: uuid.UUID,
        selection: Dict[str, Any],
        user_id: uuid.UUID | None = None,
    ) -> Dict[str, Any]:
        """
        Execute:

            Configure
            Authenticate
            Test
            Discover
            Select

        Used by ConnectorWizard.
        """

        source = await (
            self.source_repo.get_by_id(
                source_id
            )
        )

        if not source:
            raise ValueError(
                f"Data source {source_id} not found."
            )

        connector = (
            self.get_connector_for_source(
                source,
                owner_id=(
                    user_id
                    or source.owner_id
                ),
            )
        )

        result: Dict[
            str,
            Any
        ] = {
            "source_id": str(
                source.id
            ),
            "source_name": source.name,
            "source_type": source.source_type,
            "lifecycle": {},
        }

        for stage in (
            "configure",
            "authenticate",
            "test",
            "discover",
        ):
            stage_result = await (
                self._run_stage(
                    connector,
                    stage,
                )
            )

            result[
                "lifecycle"
            ][
                stage
            ] = stage_result.model_dump(
                mode="json"
            )

            if not stage_result.success:
                result[
                    "status"
                ] = stage_result.status

                result[
                    "message"
                ] = (
                    stage_result.error
                    or stage_result.message
                )

                return result

        select_result = await (
            self._run_stage(
                connector,
                "select",
                args=[
                    selection
                ],
            )
        )

        result[
            "lifecycle"
        ][
            "select"
        ] = select_result.model_dump(
            mode="json"
        )

        result[
            "status"
        ] = (
            "success"
            if select_result.success
            else select_result.status
        )

        result[
            "message"
        ] = (
            select_result.message
            or (
                "Resources selected."
                if select_result.success
                else "Resource selection failed."
            )
        )

        return result

    # =================================================================
    # CONNECTION TEST
    # =================================================================

    async def test_data_source(
        self,
        source_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Dict[str, Any]:
        """
        Execute:

            Configure
            Authenticate
            Test

        Used by the connector configuration wizard.
        """

        source = await (
            self.source_repo.get_by_id(
                source_id
            )
        )

        if not source:
            raise ValueError(
                f"Data source {source_id} not found."
            )

        connector = (
            self.get_connector_for_source(
                source,
                owner_id=(
                    user_id
                    or source.owner_id
                ),
            )
        )

        result: Dict[
            str,
            Any
        ] = {
            "source_id": str(
                source.id
            ),
            "source_name": source.name,
            "source_type": source.source_type,
            "lifecycle": {},
        }

        for stage in (
            "configure",
            "authenticate",
            "test",
        ):
            stage_result = await (
                self._run_stage(
                    connector,
                    stage,
                )
            )

            result[
                "lifecycle"
            ][
                stage
            ] = stage_result.model_dump(
                mode="json"
            )

            if not stage_result.success:
                result[
                    "status"
                ] = stage_result.status

                result[
                    "message"
                ] = (
                    stage_result.error
                    or stage_result.message
                )

                return result

        result[
            "status"
        ] = "success"

        result[
            "message"
        ] = "Connection test succeeded."

        return result

    # =================================================================
    # SOURCE MONITORING
    # =================================================================

    async def get_source_monitoring(
        self,
        source_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Return connector/source monitoring state without running a sync.
        """

        source = await (
            self.source_repo.get_by_id(
                source_id
            )
        )

        if not source:
            raise ValueError(
                f"Data source {source_id} not found."
            )

        metadata = (
            self.get_connector_metadata(
                source
            )
        )

        now = datetime.now(
            timezone.utc
        )

        last_synced = (
            source.last_synced_at
        )

        if last_synced is None:
            sync_age_seconds = None
        else:
            sync_age_seconds = max(
                0,
                int(
                    (
                        now
                        - last_synced
                    ).total_seconds()
                ),
            )

        return {
            "source_id": str(
                source.id
            ),
            "source_name": source.name,
            "source_type": source.source_type,
            "connector_id": metadata.id,
            "connector_name": metadata.name,
            "driver": (
                "native"
                if metadata.is_native
                else "universal"
            ),
            "source_status": str(
                source.status
            ),
            "last_synced_at": (
                last_synced.isoformat()
                if last_synced
                else None
            ),
            "sync_age_seconds": (
                sync_age_seconds
            ),
            "monitoring_status": (
                "never_synced"
                if last_synced is None
                else "healthy"
            ),
            "lifecycle": list(
                metadata.lifecycle
            ),
            "lifecycle_stages": {
                stage: (
                    stage
                    in metadata.lifecycle
                )
                for stage
                in CONNECTOR_LIFECYCLE
            },
        }

    # =================================================================
    # SYNC ALL
    # =================================================================

    async def sync_all_organization_sources(
        self,
        organization_id: uuid.UUID,
        use_mock_llm: bool = True,
        sync_mode: str = "continuous",
    ) -> List[SyncResult]:
        """
        Sync all registered data sources for an organization.

        Sources are processed sequentially to avoid overwhelming
        external APIs and the database.
        """

        sources = await (
            self.source_repo.list_by_organization(
                organization_id
            )
        )

        # Snapshot metadata before synchronization. This preserves
        # source information if a transaction rolls back later.
        source_metadata = [
            (
                source.id,
                source.name,
                source.source_type,
            )
            for source in sources
        ]

        results: List[
            SyncResult
        ] = []

        for (
            sid,
            sname,
            stype,
        ) in source_metadata:

            try:
                result = await (
                    self.sync_data_source(
                        sid,
                        use_mock_llm=use_mock_llm,
                        sync_mode=sync_mode,
                    )
                )

                results.append(
                    result
                )

            except Exception as exc:
                logger.exception(
                    "Organization source sync failed: %s",
                    sid,
                )

                results.append(
                    SyncResult(
                        source_id=sid,
                        source_name=sname,
                        source_type=stype,
                        documents_synced=0,
                        documents_created=0,
                        documents_updated=0,
                        documents_skipped=0,
                        claims_extracted=0,
                        conflicts_detected=0,
                        execution_time_ms=0,
                        status="error",
                        synced_at=datetime.now(
                            timezone.utc
                        ),
                        message=(
                            f"Sync failed for "
                            f"{sname}: "
                            f"{str(exc)}"
                        ),
                        monitoring={
                            "status": "error",
                            "error": str(
                                exc
                            ),
                        },
                    )
                )

        return results

    # =================================================================
    # PRIVATE RESULT HELPERS
    # =================================================================

    @staticmethod
    def _extract_stage_records(
        stage_result: LifecycleStageResult,
    ) -> List[Any]:
        """
        Extract records from a lifecycle stage result.

        Supports:

            {"records": [...]}
            {"result": [...]}
            {"data": [...]}

        and scalar values.
        """

        data = (
            stage_result.data
            or {}
        )

        records = data.get(
            "records"
        )

        if isinstance(
            records,
            list,
        ):
            return records

        result = data.get(
            "result"
        )

        if isinstance(
            result,
            list,
        ):
            return result

        data_value = data.get(
            "data"
        )

        if isinstance(
            data_value,
            list,
        ):
            return data_value

        return []

    @staticmethod
    def _finish_lifecycle(
        result: Dict[str, Any],
        *,
        status: str,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Finish a lifecycle result with a consistent status.
        """

        result[
            "status"
        ] = status

        if error:
            result[
                "error"
            ] = error

        result[
            "completed_at"
        ] = datetime.now(
            timezone.utc
        ).isoformat()

        return result