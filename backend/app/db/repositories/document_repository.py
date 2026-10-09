import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_id_with_versions(
        self,
        document_id: uuid.UUID,
    ) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        external_id: str,
    ) -> Document | None:
        stmt = select(Document).where(
            Document.organization_id == organization_id,
            Document.source_id == source_id,
            Document.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Document]:
        stmt = select(Document).where(Document.organization_id == organization_id)
        if source_id and isinstance(source_id, uuid.UUID):
            stmt = stmt.where(Document.source_id == source_id)
        stmt = (
            stmt.offset(offset)
            .limit(limit)
            .options(selectinload(Document.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_or_create_version_with_dedup(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        title: str,
        content_uri: str | None,
        content_hash: str | None,
        document_type: str | None = "policy",
        external_id: str | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> tuple[Document, DocumentVersion, bool]:
        """
        Idempotent document ingestion with SHA-256 deduplication.
        Returns:
            (document, version, is_changed: bool)
            - is_changed is True if this is a newly created document or a modified version.
            - is_changed is False if the document already exists with identical content_hash.
        """
        document = None
        if external_id:
            document = await self.get_by_external_id(
                organization_id=organization_id,
                source_id=source_id,
                external_id=external_id,
            )

        if not document:
            # Brand new document
            document = Document(
                organization_id=organization_id,
                source_id=source_id,
                owner_id=owner_id,
                title=title,
                document_type=document_type,
                external_id=external_id,
                content_uri=content_uri,
                content_hash=content_hash,
            )
            self.session.add(document)
            await self.session.flush()
            await self.session.refresh(document)

            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                content_uri=content_uri,
                content_hash=content_hash,
                is_current=True,
            )
            self.session.add(version)
            await self.session.flush()
            await self.session.refresh(version)
            return document, version, True

        # Existing document: Update owner_id if not present or passed
        if owner_id and not document.owner_id:
            document.owner_id = owner_id
            await self.session.flush()

        # Existing document: Check current active version
        current_version = await self.get_current_version(document.id)
        if current_version and current_version.content_hash and content_hash:
            if current_version.content_hash.strip().lower() == content_hash.strip().lower():
                # Document is identical -> Deduplication match (UNCHANGED)
                return document, current_version, False

        # Content is new or modified -> Create new incremented version
        stmt = (
            select(DocumentVersion.version_number)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        latest_version = res.scalar_one_or_none() or 0
        next_version_num = latest_version + 1

        # Update document header
        document.title = title
        document.content_uri = content_uri
        document.content_hash = content_hash
        await self.session.flush()

        # Deactivate existing current versions
        await self.session.execute(
            update(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .values(is_current=False)
        )
        await self.session.flush()

        # Create new current version
        new_version = DocumentVersion(
            document_id=document.id,
            version_number=next_version_num,
            content_uri=content_uri,
            content_hash=content_hash,
            is_current=True,
        )
        self.session.add(new_version)
        await self.session.flush()
        await self.session.refresh(new_version)

        return document, new_version, True

    async def create_document_with_version(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        title: str,
        content_uri: str | None,
        content_hash: str | None,
        document_type: str | None = "policy",
        external_id: str | None = None,
    ) -> tuple[Document, DocumentVersion]:
        doc, ver, _ = await self.get_or_create_version_with_dedup(
            organization_id=organization_id,
            source_id=source_id,
            title=title,
            content_uri=content_uri,
            content_hash=content_hash,
            document_type=document_type,
            external_id=external_id,
        )
        return doc, ver

    async def get_current_version(
        self,
        document_id: uuid.UUID,
    ) -> DocumentVersion | None:
        stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.is_current.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
