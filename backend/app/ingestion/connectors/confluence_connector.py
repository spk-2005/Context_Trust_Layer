import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate


class ConfluencePage(DocumentCreate):
    space_key: str = "HR"
    author: str = "admin"
    page_id: str = "1001"


class ConfluenceConnector(BaseConnector):
    """Syncs documents and wiki pages from Confluence / Knowledge base."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        space_key: str = "POLICIES",
    ):
        super().__init__(session, organization_id, source_id)
        self.space_key = space_key
        self.ingestion_service = DocumentIngestionService(session)

    async def ingest_page(
        self,
        title: str,
        content: str,
        page_id: str,
        version_num: int = 1,
        author: str = "HR Policy Team",
    ) -> tuple[Document, DocumentVersion]:
        doc_in = DocumentCreate(
            organization_id=self.organization_id,
            source_id=self.source_id,
            title=title,
            content=content,
            document_type="policy",
            external_id=f"confluence://{self.space_key}/{page_id}",
            metadata={"space": self.space_key, "author": author, "upstream_version": version_num},
        )
        return await self.ingestion_service.ingest_document(doc_in)

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        # Simulated sync of designated policy service pages
        sample_pages = [
            (
                "Customer Refund & Exception Policy 2026",
                "# Refund Policy 2026\n\nStandard refund window is 30 days.\n\n# Enterprise Exception\n\nEnterprise customers have a 60-day exception window.",
                "page-refund-2026",
            ),
            (
                "IT Security & Access Guidelines",
                "# Access Protocol\n\nAll production access requires 2-factor authentication.\n\n# Password Rotation\n\nPasswords expire every 90 days.",
                "page-security-access",
            ),
        ]
        synced: list[tuple[Document, DocumentVersion]] = []
        for title, content, pid in sample_pages:
            res = await self.ingest_page(title=title, content=content, page_id=pid)
            synced.append(res)
        return synced
