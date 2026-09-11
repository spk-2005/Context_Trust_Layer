import os
import uuid
from pathlib import Path
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate


class FileConnector(BaseConnector):
    """Ingests local documents (.md, .txt, .json) from a directory or raw content."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        directory_path: str | Path | None = None,
    ):
        super().__init__(session, organization_id, source_id)
        self.directory_path = Path(directory_path) if directory_path else None
        self.ingestion_service = DocumentIngestionService(session)

    async def ingest_single_file(
        self,
        title: str,
        content: str,
        document_type: str = "policy",
        external_id: str | None = None,
        metadata: dict | None = None,
    ) -> tuple[Document, DocumentVersion]:
        doc_in = DocumentCreate(
            organization_id=self.organization_id,
            source_id=self.source_id,
            title=title,
            content=content,
            document_type=document_type,
            external_id=external_id,
            metadata=metadata,
        )
        doc, ver, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
        return doc, ver

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        results: list[tuple[Document, DocumentVersion]] = []
        if not self.directory_path or not self.directory_path.exists():
            return results

        for file_path in self.directory_path.glob("**/*"):
            if file_path.suffix.lower() in [".md", ".txt", ".json"]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    title = file_path.stem.replace("-", " ").replace("_", " ").title()
                    doc, version = await self.ingest_single_file(
                        title=title,
                        content=content,
                        document_type="policy",
                        external_id=f"file://{file_path.name}",
                        metadata={"filename": file_path.name, "size": len(content)},
                    )
                    results.append((doc, version))
                except Exception as e:
                    print(f"[FileConnector Error] Failed to ingest {file_path}: {e}")

        return results
