import uuid
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.base import DiscoveredAsset, RawSourceAsset, SourceFamily, SyncMode, UnifiedConnector


class BaseConnector(UnifiedConnector, ABC):
    """Abstract Base Class for Data Source Connectors in Layer 2."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        owner_id: uuid.UUID | None = None,
        connection_config: dict[str, Any] | None = None,
    ):
        super().__init__(
            session=session,
            organization_id=organization_id,
            source_id=source_id,
            connection_config=connection_config,
            owner_id=owner_id,
        )

    @abstractmethod
    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Sync records from external source into documents and document_versions (legacy bridge)."""
        pass

    async def discover_assets(self) -> List[DiscoveredAsset]:
        """Default discovery implementation."""
        return []

    async def fetch_native_assets(
        self,
        selected_asset_ids: Optional[List[str]] = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: Optional[dict[str, Any]] = None,
    ) -> List[RawSourceAsset]:
        """Default native asset fetch implementation."""
        return []

