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
        """Syncs all pages from Confluence. Uses live REST API if configured, otherwise simulated live feed."""
        if self.base_url and self.api_token and self.user_email:
            return await self._sync_live_confluence()
        return await self._sync_simulated_confluence()

    async def _sync_live_confluence(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        url = f"{self.base_url}/wiki/rest/api/content?spaceKey={self.space_key}&expand=body.storage,version,history"
        auth = (self.user_email, self.api_token)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, auth=auth)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    pid = item.get("id")
                    title = item.get("title", f"Confluence Page {pid}")
                    body_html = item.get("body", {}).get("storage", {}).get("value", "")
                    ver_num = item.get("version", {}).get("number", 1)
                    # Strip simple html tags for plain text/markdown
                    clean_content = body_html.replace("<p>", "").replace("</p>", "\n\n").replace("<h1>", "# ").replace("</h1>", "\n\n")
                    res = await self.ingest_page(title=title, content=clean_content, page_id=pid, version_num=ver_num)
                    synced.append(res)
        return synced

    async def _sync_simulated_confluence(self) -> list[tuple[Document, DocumentVersion]]:
        # Realistic enterprise Confluence policy feed
        pages = [
            (
                "Executive Customer Exception & Dispute Policy",
                "# Customer Exception Protocol\n\nStandard customer claims must be evaluated against official purchase receipts within 30 days.\n\n# Tier-1 Enterprise Exceptions\n\nEnterprise accounts with dedicated CSM coverage may request exception reviews up to ₹50,000 with VP authorization.",
                "CONF-PAGE-DISPUTES",
                2,
                "Sarah Chen (Lead Auditor)",
            ),
            (
                "Global Information Security Standard 2026",
                "# Information Security Mandate\n\nAll external services interacting with user records must enforce AES-256 encryption at rest.\n\n# Audit Retention\n\nSecurity logs and administrative access records must be immutable and retained for 7 years.",
                "CONF-PAGE-INFOSEC-2026",
                1,
                "CISO Office",
            ),
        ]
        synced = []
        for title, content, pid, ver, author in pages:
            res = await self.ingest_page(title=title, content=content, page_id=pid, version_num=ver, author=author)
            synced.append(res)
        return synced
