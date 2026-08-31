import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


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


# Alias for backwards compatibility with legacy connectors
RawDocumentPayload = RawDocument


class BaseConnector(ABC):
    @abstractmethod
    async def fetch_document(self, external_id: str) -> RawDocument:
        """Fetch raw document payload from third-party source."""
        pass

