import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.repositories.document_repository import DocumentRepository
from app.ingestion.base import RawDocument
from app.normalization.normalizer import DocumentNormalizer, NormalizedDocument
from app.schemas.document import DocumentCreate


class DocumentIngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.normalizer = DocumentNormalizer()

    @staticmethod
    def calculate_hash(content: str) -> str:
        return DocumentNormalizer.compute_content_hash(content)

    def normalize_payload(
        self,
        raw_doc: RawDocument | DocumentCreate,
    ) -> NormalizedDocument:
        """Normalizes and validates incoming document payload."""
        doc_type = getattr(raw_doc, "document_type", "document") or "document"
        metadata = getattr(raw_doc, "metadata", None) or {}
        author = getattr(raw_doc, "author", None)
        created_at = getattr(raw_doc, "created_at", None)
        updated_at = getattr(raw_doc, "updated_at", None)

        return self.normalizer.normalize(
            title=raw_doc.title,
            content=raw_doc.content,
            organization_id=raw_doc.organization_id,
            source_id=raw_doc.source_id,
            document_type=doc_type,
            external_id=raw_doc.external_id,
            author=author,
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata,
        )

    async def ingest_document_with_dedup(
        self,
        doc_in: DocumentCreate | RawDocument,
    ) -> tuple[Document, DocumentVersion, NormalizedDocument, bool]:
        """Ingests document returning is_changed=False if content_hash matches current version."""
        # 1. Execute canonical normalization and domain validation
        normalized = self.normalize_payload(doc_in)

        # 2. Compute SHA-256 content hash
        content_hash = self.normalizer.compute_content_hash(normalized.content)
        content_uri = normalized.content

        # 3. Create or match existing version via deduplication
        owner_id = getattr(doc_in, "owner_id", None)
        document, version, is_changed = await self.doc_repo.get_or_create_version_with_dedup(
            organization_id=normalized.organization_id,
            source_id=normalized.source_id,
            title=normalized.title,
            content_uri=content_uri,
            content_hash=content_hash,
            document_type=normalized.document_type,
            external_id=normalized.external_id,
            owner_id=owner_id,
        )

        return document, version, normalized, is_changed

    async def ingest_document(
        self,
        doc_in: DocumentCreate | RawDocument,
    ) -> tuple[Document, DocumentVersion, NormalizedDocument]:
        document, version, normalized, _ = await self.ingest_document_with_dedup(doc_in)
        return document, version, normalized

