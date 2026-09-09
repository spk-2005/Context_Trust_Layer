import os
import uuid
from typing import Sequence

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate


class ConfluenceConnector(BaseConnector):
    """Syncs documents, SOPs, and policies from Atlassian Confluence spaces."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        space_key: str = "POLICIES",
        base_url: str | None = None,
        api_token: str | None = None,
        user_email: str | None = None,
    ):
        super().__init__(session, organization_id, source_id)
        self.space_key = space_key or "POLICIES"
        self.base_url = (base_url or os.getenv("CONFLUENCE_BASE_URL", "")).rstrip("/")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN", "")
        self.user_email = user_email or os.getenv("CONFLUENCE_USER_EMAIL", "")
        self.ingestion_service = DocumentIngestionService(session)

    async def ingest_page(
        self,
        title: str,
        content: str,
        page_id: str,
        version_num: int = 1,
        author: str = "Confluence Author",
    ) -> tuple[Document, DocumentVersion]:
        doc_in = DocumentCreate(
            organization_id=self.organization_id,
            source_id=self.source_id,
            title=title.replace("\x00", "").strip(),
            content=content.replace("\x00", "").strip(),
            document_type="confluence_page",
            external_id=f"confluence://{self.space_key}/{page_id}",
            metadata={
                "space": self.space_key,
                "author": author,
                "upstream_version": version_num,
                "connector": "confluence",
            },
        )
        doc, version, _ = await self.ingestion_service.ingest_document(doc_in)
        return doc, version

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Syncs live pages from Confluence using REST API."""
        if not self.base_url or not self.api_token or not self.user_email:
            raise RuntimeError(
                f"Confluence live sync requires 'base_url', 'api_token', and 'user_email' for space '{self.space_key}'."
            )

        try:
            return await self._sync_live_confluence()
        except Exception as e:
            raise RuntimeError(f"Confluence sync failed for space '{self.space_key}': {str(e)}")

    async def _sync_live_confluence(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        url = f"{self.base_url}/wiki/rest/api/content?spaceKey={self.space_key}&expand=body.storage,version,history"
        auth = (self.user_email, self.api_token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, auth=auth)
            if resp.status_code != 200:
                raise RuntimeError(f"Confluence API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            for item in data.get("results", []):
                pid = item.get("id")
                title = item.get("title", f"Confluence Page {pid}")
                body_html = item.get("body", {}).get("storage", {}).get("value", "")
                ver_num = item.get("version", {}).get("number", 1)
                clean_content = body_html.replace("<p>", "").replace("</p>", "\n\n").replace("<h1>", "# ").replace("</h1>", "\n\n")
                res = await self.ingest_page(title=title, content=clean_content, page_id=pid, version_num=ver_num)
                synced.append(res)
        return synced
