from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class RawDocumentPayload(BaseModel):
    title: str
    content: str
    source_type: str
    external_id: str | None = None
    document_type: str | None = "policy"
    metadata: dict[str, Any] = {}


class BaseConnector(ABC):
    @abstractmethod
    async def fetch_document(self, external_id: str) -> RawDocumentPayload:
        """Fetch raw document payload from third-party source."""
        pass
