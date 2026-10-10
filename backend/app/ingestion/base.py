import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, List, Optional
from pydantic import BaseModel, Field

from app.db.enums import SourceFamily, SourceIntent
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion


class SyncMode(str, Enum):
    INITIAL_FULL = "initial_full"
    INCREMENTAL_DELTA = "incremental_delta"


class SourceFamily(str, Enum):
    DOCUMENT = "document"          # PDF, DOCX, Markdown, HTML, Plaintext
    STRUCTURED = "structured"      # PostgreSQL, MySQL, MongoDB, JSON, CSV, Data Warehouse
    CONVERSATION = "conversation"  # Jira, Slack, Teams, Email, GitHub PR Comments
    METADATA = "metadata"          # BI definitions, ETL/Lineage, Schemas, Config, Logs


class SyncMode(str, Enum):
    INITIAL_FULL = "initial_full"
    INCREMENTAL_DELTA = "incremental_delta"
    TOMBSTONE_CLEANUP = "tombstone_cleanup"


class DiscoveredAsset(BaseModel):
    """Hierarchical asset discovered within an external data source."""

    asset_id: str                      # Unique upstream identifier (e.g. "table:public.users", "file:docs/sla.md")
    name: str                          # Human-readable title
    asset_type: str                    # "table", "collection", "file", "project", "space", "topic"
    source_family: SourceFamily
    parent_id: Optional[str] = None
    estimated_size_bytes: Optional[int] = None
    last_modified_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawSourceAsset(BaseModel):
    """Represents an un-flattened native asset payload emitted by Layer 2 connectors."""

    asset_id: str
    source_family: SourceFamily
    native_format: str                 # "json", "sql_rows", "markdown", "jira_issue", "confluence_page", "pdf"
    source_version: str                # commit SHA, timestamp, row hash, version number
    raw_payload: Any                   # Native Python dict, list of row dicts, or raw string
    locator_metadata: dict[str, Any] = Field(default_factory=dict)  # Native coordinates (table, PK, file path, line range)
    content_hash: str = ""             # SHA-256 hash of native payload
    is_deleted: bool = False           # True if this is a tombstone event (asset deleted upstream)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash:
            if isinstance(self.raw_payload, (dict, list)):
                dumped = json.dumps(self.raw_payload, sort_keys=True, default=str)
                self.content_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
            elif isinstance(self.raw_payload, str):
                self.content_hash = hashlib.sha256(self.raw_payload.encode("utf-8")).hexdigest()
            else:
                self.content_hash = hashlib.sha256(str(self.raw_payload).encode("utf-8")).hexdigest()


class ConnectorCapability(BaseModel):
    """Declares the capabilities and supported modes of a connector driver."""

    connector_type: str
    display_name: str
    source_families: List[SourceFamily] = Field(default_factory=list)
    supports_discovery: bool = True
    supports_delta_sync: bool = True
    supports_tombstones: bool = True
    supports_webhooks: bool = False
    auth_schemes: List[str] = Field(default_factory=lambda: ["api_key", "bearer_token", "basic", "uri"])


class UnifiedConnector(ABC):
    """Standardized Layer 2 contract for all connectors in the Context Trust Layer."""

    def __init__(
        self,
        session: Any = None,
        organization_id: Optional[uuid.UUID] = None,
        source_id: Optional[uuid.UUID] = None,
        connection_config: Optional[dict[str, Any]] = None,
        owner_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ):
        self.session = session
        self.organization_id = organization_id
        self.source_id = source_id
        self.connection_config = connection_config or {}
        self.owner_id = owner_id

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """Validates credentials, permissions, and network connectivity."""
        pass

    @abstractmethod
    async def discover_assets(self) -> List[DiscoveredAsset]:
        """Discovers available tables, folders, collections, spaces, or repositories."""
        pass

    @abstractmethod
    async def fetch_native_assets(
        self,
        selected_asset_ids: Optional[List[str]] = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: Optional[dict[str, Any]] = None,
    ) -> List[RawSourceAsset]:
        """Streams or batches native un-flattened source assets with delta checkpointing."""
        pass

    async def sync(self) -> List[Any]:
        """Legacy compatibility sync bridge."""
        return []


# Backwards compatibility models
class RawDocument(BaseModel):
    """Represents an un-normalized ingress document payload from connector integration."""
    organization_id: uuid.UUID
    source_id: uuid.UUID
    title: str
    content: str
    document_type: str = "document"
    external_id: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


RawDocumentPayload = RawDocument


class DiscoveredAsset(BaseModel):
    """Layer 2 Discovered Asset specification."""
    id: str = Field(..., description="Unique entity identifier or path")
    name: str = Field(..., description="Human readable name")
    asset_type: str = Field(..., description="table, view, collection, file, directory, channel, space, project")
    parent_scope: str | None = None
    is_selectable: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def item_type(self) -> str:
        """Alias for Layer 1 compatibility."""
        return self.asset_type


class RawSourceAsset(BaseModel):
    """Layer 2 native un-flattened payload (SQL row, JSON document, AST, chat thread)."""
    asset_id: str
    source_id: uuid.UUID
    source_family: SourceFamily
    source_version: str = "v1"
    native_format: str  # "sql_row", "json", "markdown", "chat_thread", etc.
    raw_payload: Any
    evidence_locator: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UnifiedConnector(ABC):
    """
    Harmonized Base Connector contract unifying Layer 1 (intent, scoping, inventory)
    and Layer 2 (asset discovery, native asset streaming, checkpointing).
    """

    def __init__(
        self,
        session: Any = None,
        organization_id: uuid.UUID | None = None,
        source_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        scope_config: dict[str, Any] | None = None,
        source_intent: SourceIntent | None = None,
        connection_config: dict[str, Any] | None = None,
    ):
        self.session = session
        self.organization_id = organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
        self.source_id = source_id or uuid.uuid4()
        self.owner_id = owner_id
        self.scope_config = scope_config or {}
        self.connection_config = connection_config or {}
        self._source_intent = source_intent or SourceIntent.GOVERNANCE_POLICY

    @property
    def source_family(self) -> SourceFamily:
        return SourceFamily.DOCUMENT

    @property
    def source_intent(self) -> SourceIntent:
        return self._source_intent

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_incremental": False,
            "supports_cdc": False,
            "supports_schema_discovery": False,
            "supports_granular_selection": False,
            "supports_snapshots": True,
        }

    @abstractmethod
    async def fetch_document(self, external_id: str) -> RawDocument:
        """Fetch raw document payload from third-party source (legacy)."""
        pass


    async def test_connection(self) -> dict[str, Any]:
        """Validates auth, host connectivity, and read permissions."""
        pass

    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Layer 2 standard: Discovers schemas, tables, collections, files, spaces."""
        return []

    async def discover_inventory(self) -> dict[str, Any]:
        """Layer 1 compatibility helper wrapping discover_assets()."""
        assets = await self.discover_assets()
        items = [
            {
                "id": a.id,
                "name": a.name,
                "item_type": a.asset_type,
                "parent": a.parent_scope,
                "is_selectable": a.is_selectable,
                "metadata": a.metadata,
            }
            for a in assets
        ]
        return {
            "source_id": str(self.source_id),
            "source_family": self.source_family.value,
            "assets_count": len(assets),
            "items": items,
            "assets": [a.model_dump() for a in assets],
            "total_count": len(items),
        }

    async def validate_scope(self, scope_config: dict[str, Any]) -> dict[str, Any]:
        """Validates that requested entities in scope_config exist and are accessible."""
        return {"valid": True, "message": "Scope configuration accepted."}

    async def fetch_native_assets(
        self,
        selected_asset_ids: list[str] | None = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: dict[str, Any] | None = None,
    ) -> list[RawSourceAsset]:
        """Layer 2: Emits raw un-flattened payloads (SQL rows, JSON documents, ASTs)."""
        return []

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Legacy sync method for backwards compatibility."""
        return []


BaseSourceAdapter = UnifiedConnector
BaseConnector = UnifiedConnector
