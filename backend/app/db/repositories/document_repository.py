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
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Document]:
        stmt = (
            select(Document)
            .where(Document.organization_id == organization_id)
            .offset(offset)
            .limit(limit)
            .options(selectinload(Document.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

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
        # 1. Check if document exists
        document = None
        if external_id:
            document = await self.get_by_external_id(
                organization_id=organization_id,
                source_id=source_id,
                external_id=external_id,
            )

        if not document:
            document = Document(
                organization_id=organization_id,
                source_id=source_id,
                title=title,
                document_type=document_type,
                external_id=external_id,
                content_uri=content_uri,
                content_hash=content_hash,
            )
            self.session.add(document)
            await self.session.flush()
            await self.session.refresh(document)
            next_version_num = 1
        else:
            # Find next version number
            stmt = select(DocumentVersion.version_number).where(
                DocumentVersion.document_id == document.id
            ).order_by(DocumentVersion.version_number.desc()).limit(1)
            res = await self.session.execute(stmt)
            latest_version = res.scalar_one_or_none() or 0
            next_version_num = latest_version + 1

            # Update document content hash and title
            document.title = title
            document.content_uri = content_uri
            document.content_hash = content_hash
            await self.session.flush()

        # 2. Deactivate existing current versions
        await self.session.execute(
            update(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .values(is_current=False)
        )
        await self.session.flush()

        # 3. Create new current version
        version = DocumentVersion(
            document_id=document.id,
            version_number=next_version_num,
            content_uri=content_uri,
            content_hash=content_hash,
            is_current=True,
        )
        self.session.add(version)
        await self.session.flush()
        await self.session.refresh(version)

        return document, version

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
