import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, List, Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import SourceFamily, SourceIntent
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion


class SyncMode(str, Enum):
    INITIAL_FULL = "initial_full"
    INCREMENTAL_DELTA = "incremental_delta"
    TOMBSTONE_CLEANUP = "tombstone_cleanup"


class DiscoveredAsset(BaseModel):
    """Hierarchical asset discovered within an external data source."""

    id: Optional[str] = None
    asset_id: Optional[str] = None      # Unique upstream identifier (e.g. "table:public.users", "file:docs/sla.md")
    name: str                          # Human-readable title
    asset_type: str                    # "table", "collection", "file", "project", "space", "topic"
    source_family: SourceFamily = SourceFamily.DOCUMENT
    parent_id: Optional[str] = None
    parent_scope: Optional[str] = None
    is_selectable: bool = True
    estimated_size_bytes: Optional[int] = None
    last_modified_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.asset_id and self.id:
            self.asset_id = self.id
        elif not self.id and self.asset_id:
            self.id = self.asset_id
        if not self.parent_id and self.parent_scope:
            self.parent_id = self.parent_scope
        elif not self.parent_scope and self.parent_id:
            self.parent_scope = self.parent_id

    @property
    def item_type(self) -> str:
        """Alias for Layer 1 compatibility."""
        return self.asset_type


class RawSourceAsset(BaseModel):
    """Represents an un-flattened native asset payload emitted by Layer 2 connectors."""

    asset_id: str
    source_id: Optional[uuid.UUID] = None
    source_family: SourceFamily = SourceFamily.DOCUMENT
    native_format: str = "json"        # "json", "sql_rows", "markdown", "jira_issue", "confluence_page", "pdf"
    source_version: str = "1"          # commit SHA, timestamp, row hash, version number
    raw_payload: Any = None            # Native Python dict, list of row dicts, or raw string
    locator_metadata: dict[str, Any] = Field(default_factory=dict)  # Native coordinates
    evidence_locator: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""             # SHA-256 hash of native payload
    is_deleted: bool = False           # True if this is a tombstone event (asset deleted upstream)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash:
            if isinstance(self.raw_payload, (dict, list)):
                dumped = json.dumps(self.raw_payload, sort_keys=True, default=str)
                self.content_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
            elif isinstance(self.raw_payload, str):
                self.content_hash = hashlib.sha256(self.raw_payload.encode("utf-8")).hexdigest()
            else:
                self.content_hash = hashlib.sha256(str(self.raw_payload).encode("utf-8")).hexdigest()
        if not self.locator_metadata and self.evidence_locator:
            self.locator_metadata = self.evidence_locator
        elif not self.evidence_locator and self.locator_metadata:
            self.evidence_locator = self.locator_metadata


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
    """
    Harmonized Base Connector contract unifying Layer 1 (intent, scoping, inventory)
    and Layer 2 (asset discovery, native asset streaming, checkpointing).
    """

    def __init__(
        self,
        session: Any = None,
        organization_id: Optional[uuid.UUID] = None,
        source_id: Optional[uuid.UUID] = None,
        connection_config: Optional[dict[str, Any]] = None,
        owner_id: Optional[uuid.UUID] = None,
        scope_config: Optional[dict[str, Any]] = None,
        source_intent: Optional[SourceIntent] = None,
        **kwargs: Any,
    ):
        self.session = session
        self.organization_id = organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
        self.source_id = source_id or uuid.uuid4()
        self.connection_config = connection_config or {}
        self.owner_id = owner_id
        self.scope_config = scope_config or {}
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
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
        }

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """Validates credentials, permissions, and network connectivity."""
        pass

    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Layer 2 standard: Discovers schemas, tables, collections, files, spaces."""
        return []

    async def discover_inventory(self) -> dict[str, Any]:
        """Layer 1 compatibility helper wrapping discover_assets()."""
        assets = await self.discover_assets()
        items = [
            {
                "id": a.asset_id or a.id,
                "name": a.name,
                "item_type": a.asset_type,
                "parent": a.parent_id or a.parent_scope,
                "is_selectable": a.is_selectable,
                "metadata": a.metadata,
            }
            for a in assets
        ]
        return {
            "source_id": str(self.source_id),
            "source_family": self.source_family.value if hasattr(self.source_family, "value") else str(self.source_family),
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
        selected_asset_ids: Optional[list[str]] = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: Optional[dict[str, Any]] = None,
    ) -> list[RawSourceAsset]:
        """Streams or batches native un-flattened source assets with delta checkpointing."""
        return []

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Legacy compatibility sync bridge."""
        return []


# Backwards compatibility aliases
class RawDocument(BaseModel):
    """Represents an un-normalized ingress document payload from connector integration (legacy)."""
    model_config = ConfigDict(extra="allow")
    organization_id: Optional[uuid.UUID] = Field(default_factory=lambda: uuid.UUID("11111111-1111-1111-1111-111111111111"))
    source_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
    title: str
    content: str
    document_type: str = "document"
    source_type: Optional[str] = None
    external_id: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


RawDocumentPayload = RawDocument
BaseSourceAdapter = UnifiedConnector
BaseConnector = UnifiedConnector

