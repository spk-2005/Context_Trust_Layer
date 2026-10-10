import uuid
from typing import Any, Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceFamily, SourceIntent
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.base import (
    DiscoveredAsset,
    RawSourceAsset,
    SyncMode,
    UnifiedConnector,
    BaseSourceAdapter,
)

# Re-export for connector implementations
BaseConnector = UnifiedConnector

__all__ = [
    "UnifiedConnector",
    "BaseConnector",
    "BaseSourceAdapter",
    "DiscoveredAsset",
    "RawSourceAsset",
    "SyncMode",
]
