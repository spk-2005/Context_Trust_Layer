import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentCreate


class DocumentIngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.doc_repo = DocumentRepository(session)

    @staticmethod
    def calculate_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def ingest_document(
        self,
        doc_in: DocumentCreate,
    ) -> tuple[Document, DocumentVersion]:
        content_hash = self.calculate_hash(doc_in.content)
        content_uri = doc_in.content  # For local/raw text storage or reference

        document, version = await self.doc_repo.create_document_with_version(
            organization_id=doc_in.organization_id,
            source_id=doc_in.source_id,
            title=doc_in.title,
            content_uri=content_uri,
            content_hash=content_hash,
            document_type=doc_in.document_type,
            external_id=doc_in.external_id,
        )

        return document, version
