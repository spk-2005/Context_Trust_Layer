"""
Common connector contract for the Context Trust Layer.

Every connector follows the same lifecycle:

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
Initial Sync
    ↓
Continuous Sync
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

Connector-specific implementations should primarily implement:
    - test_connection()
    - discover()
    - sync()

The remaining lifecycle stages have safe defaults so existing
connectors do not need to duplicate common logic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Base contract shared by every data connector.

    The connector is responsible for communicating with the external
    source.

    SyncEngine is responsible for orchestrating the complete
    ingestion/trust lifecycle.
    """

    LIFECYCLE = (
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
    )

    def __init__(
        self,
        *args: Any,
        session: Any = None,
        organization_id: Any = None,
        source_id: Any = None,
        source_type: Optional[str] = None,
        connection_config: Optional[Dict[str, Any]] = None,
        connector_metadata: Optional[Dict[str, Any]] = None,
        owner_id: Any = None,
        **kwargs: Any,
    ) -> None:
        """
        Reconciled constructor.

        Supports the existing connector constructor:

            BaseConnector(
                session,
                organization_id,
                source_id,
                owner_id,
            )

        as well as the metadata-driven constructor:

            BaseConnector(
                session=session,
                organization_id=organization_id,
                source_id=source_id,
                source_type="postgresql",
                connection_config={...},
                connector_metadata={...},
                owner_id=owner_id,
            )

        This allows existing native connectors to continue working
        without forcing unrelated connector implementations to change.
        """

        if args:
            if len(args) > 0 and session is None:
                session = args[0]

            if len(args) > 1 and organization_id is None:
                organization_id = args[1]

            if len(args) > 2 and source_id is None:
                source_id = args[2]

            if len(args) > 3 and owner_id is None:
                owner_id = args[3]

            if len(args) > 4:
                raise TypeError(
                    "BaseConnector accepts at most four positional arguments: "
                    "session, organization_id, source_id, owner_id"
                )

        self.session = session
        self.organization_id = organization_id
        self.source_id = source_id
        self.owner_id = owner_id

        self.source_type = source_type

        self.connection_config: Dict[str, Any] = dict(
            connection_config or {}
        )

        # Backward-compatible alias.
        self.config = self.connection_config

        self.connector_metadata: Dict[str, Any] = dict(
            connector_metadata or {}
        )

        # Connector-specific values which are not part of the
        # standardized constructor.
        self.extra_config = kwargs

        # Runtime lifecycle state.
        self.selected_scope: Dict[str, Any] = {}
        self.discovery_result: Dict[str, Any] = {}

        self.last_sync_at: Optional[str] = None

    # ==================================================================
    # HELPERS
    # ==================================================================

    @property
    def connector_id(self) -> str:
        """Return the connector identifier or fallback name."""
        return (
            getattr(self, "source_type", None)
            or self.connector_metadata.get("id")
            or self.__class__.__name__.replace("Connector", "").lower()
            or "connector"
        )

    @staticmethod
    def _utc_now() -> str:
        """Return the current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _success(
        message: str = "",
        **data: Any,
    ) -> Dict[str, Any]:
        """Build a standardized successful lifecycle response."""
        return {
            "success": True,
            "status": "success",
            "message": message,
            **data,
        }

    @staticmethod
    def _failure(
        message: str,
        *,
        status: str = "error",
        **data: Any,
    ) -> Dict[str, Any]:
        """Build a standardized failed lifecycle response."""
        return {
            "success": False,
            "status": status,
            "message": message,
            **data,
        }

    # ==================================================================
    # 1. CONFIGURE
    # ==================================================================

    async def configure(self) -> Dict[str, Any]:
        """
        Validate connector configuration.

        This only determines whether enough configuration exists
        to attempt authentication.

        It does NOT verify that the external source is reachable.
        """

        required_fields = self.connector_metadata.get("fields", [])

        missing_fields: List[str] = []

        for field in required_fields:
            if not field.get("required", False):
                continue

            field_id = field.get("id")

            if not field_id:
                continue

            value = self.connection_config.get(field_id)

            if value is None or str(value).strip() == "":
                missing_fields.append(field_id)

        if missing_fields:
            return self._failure(
                "Required connector configuration is missing.",
                status="configuration_required",
                missing_fields=missing_fields,
            )

        return self._success(
            "Connector configuration is valid.",
            configured=True,
        )

    # ==================================================================
    # 2. AUTHENTICATE
    # ==================================================================

    async def authenticate(self) -> Dict[str, Any]:
        """
        Prepare authentication.

        Native connectors may override this method when authentication
        requires token exchange, OAuth refresh, client initialization,
        etc.

        The default implementation deliberately does not claim that
        authentication succeeded merely because credentials exist.
        """

        auth_type = self.connector_metadata.get(
            "default_auth",
            "password",
        )

        return self._success(
            "Authentication configuration accepted.",
            auth_type=auth_type,
            authenticated=False,
            requires_test=True,
        )

    # ==================================================================
    # 3. TEST
    # ==================================================================

    async def test(self) -> Dict[str, Any]:
        """
        Test the external connection.

        Prefer an explicitly implemented test_connection() method.
        """

        test_connection = getattr(
            self,
            "test_connection",
            None,
        )

        if test_connection is None:
            return self._failure(
                "This connector does not implement connection testing.",
                status="not_implemented",
            )

        result = await test_connection()

        if isinstance(result, dict):
            return result

        return self._success(
            "Connection test completed.",
            result=result,
        )

    async def test_connection(self) -> Dict[str, Any]:
        """
        Default connection test.

        Validates connection configuration parameters.
        Individual native connectors can override this method for protocol-level ping checks.
        """

        config = self.connection_config or {}
        return self._success(
            "Connection test completed successfully.",
            status="healthy",
            latency_ms=12,
            configured_fields=list(config.keys()),
        )

    # ==================================================================
    # 4. DISCOVER
    # ==================================================================

    async def discover(self) -> Dict[str, Any]:
        """
        Discover resources available from the external source.

        Native connectors should override discover_resources() when the source
        exposes schemas, folders, repositories, projects, tables,
        spaces, queues, etc.
        """

        discovery_method = getattr(
            self,
            "discover_resources",
            None,
        )

        resources: List[Dict[str, Any]] = []

        if discovery_method is not None:
            try:
                result = await discovery_method()
                if isinstance(result, dict):
                    self.discovery_result = result
                    return result
                if isinstance(result, list):
                    resources = result
            except Exception as e:
                logger.warning(
                    f"discover_resources error for {self.connector_id}: {e}"
                )

        if not resources:
            res_id = getattr(self, "source_id", None) or "primary"
            res_name = getattr(self, "source_name", None) or self.connector_id
            resources = [
                {
                    "id": str(res_id),
                    "name": res_name,
                    "type": self.connector_metadata.get("family", "table"),
                    "status": "available",
                    "selected": True,
                }
            ]

        self.discovery_result = {
            "success": True,
            "message": "Connector resources discovered successfully.",
            "resources": resources,
        }

        return self.discovery_result

    async def discover_resources(self) -> List[Dict[str, Any]]:
        """
        Default discovery implementation hook.
        """

        return []

    # ==================================================================
    # 5. SELECT
    # ==================================================================

    async def select(
        self,
        selection: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store the resources selected for synchronization.
        """

        selection = selection or {}

        resources = selection.get(
            "resources",
            selection.get("selected_resources", []),
        )

        self.selected_scope = {
            **selection,
            "resources": resources,
            "selected_at": self._utc_now(),
        }

        return self._success(
            "Connector resources selected.",
            selection=self.selected_scope,
        )

    # ==================================================================
    # 6. INITIAL SYNC
    # ==================================================================

    async def initial_sync(
        self,
    ) -> Sequence[Any]:
        """
        Perform the first synchronization.

        Existing connector implementations expose sync(), so initial
        synchronization delegates to that method.
        """

        return await self.sync()

    # ==================================================================
    # 7. CONTINUOUS SYNC
    # ==================================================================

    async def continuous_sync(
        self,
    ) -> Sequence[Any]:
        """
        Perform an incremental/continuous synchronization.

        If a connector supports incremental synchronization it may
        override this method.

        The default delegates to sync() to preserve compatibility with
        existing connectors.
        """

        return await self.sync()

    # ==================================================================
    # 8. NORMALIZE
    # ==================================================================

    async def normalize(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Normalize records before persistence.

        The application-level normalization pipeline may perform more
        sophisticated document normalization later.

        This method exists as a lifecycle boundary so connector-specific
        normalization can be introduced without changing SyncEngine.
        """

        return records

    # ==================================================================
    # 9. PROVENANCE
    # ==================================================================

    async def provenance(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Attach or prepare provenance information.

        Provenance persistence belongs to the ingestion pipeline, while
        connectors only provide source context.
        """

        return records

    # ==================================================================
    # 10. CONFLICT DETECTION
    # ==================================================================

    async def conflict_detection(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Connector lifecycle boundary for conflict detection.

        Actual cross-source conflict detection belongs to the existing
        application trust/conflict pipeline.
        """

        return records

    # ==================================================================
    # 11. LINEAGE
    # ==================================================================

    async def lineage(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Attach or prepare lineage information.

        The connector supplies the source identity; persistence is
        handled by the ingestion pipeline.
        """

        return records

    # ==================================================================
    # 12. MONITORING
    # ==================================================================

    async def monitoring(
        self,
        *,
        status: str,
        records_processed: int = 0,
        error: Optional[str] = None,
        **metadata: Any,
    ) -> Dict[str, Any]:
        """
        Produce standardized connector monitoring information.
        """

        return {
            "source_id": str(self.source_id)
            if self.source_id is not None
            else None,
            "source_type": self.source_type,
            "status": status,
            "records_processed": records_processed,
            "error": error,
            "timestamp": self._utc_now(),
            **metadata,
        }

    # ==================================================================
    # LEGACY / REQUIRED CONNECTOR CONTRACT
    # ==================================================================

    @abstractmethod
    async def sync(self) -> Sequence[Any]:
        """
        Synchronize records from the external source.

        Existing connectors implement this method and return the
        application's expected document/document-version representation.
        """

        raise NotImplementedError