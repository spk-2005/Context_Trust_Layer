import uuid
from abc import ABC, abstractmethod
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion


class BaseConnector(ABC):
    """Abstract Base Class for Data Source Connectors."""

    def __init__(self, session: AsyncSession, organization_id: uuid.UUID, source_id: uuid.UUID):
        self.session = session
        self.organization_id = organization_id
        self.source_id = source_id

    @abstractmethod
    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Sync records from external source into documents and document_versions."""
        pass
