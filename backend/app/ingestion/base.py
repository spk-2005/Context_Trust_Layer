import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, List, Optional
from pydantic import BaseModel, Field


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
    """Represents an un-normalized ingress document payload (legacy compatibility)."""

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


class BaseConnector(ABC):
    @abstractmethod
    async def fetch_document(self, external_id: str) -> RawDocument:
        """Fetch raw document payload from third-party source (legacy)."""
        pass


