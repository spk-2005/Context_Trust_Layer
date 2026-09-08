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


class JiraConnector(BaseConnector):
    """Syncs live release policies, operational runbooks, and incident rules from Atlassian Jira."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        project_key: str = "OPS",
        base_url: str | None = None,
        api_token: str | None = None,
        user_email: str | None = None,
    ):
        super().__init__(session, organization_id, source_id)
        self.project_key = project_key or "OPS"
        self.base_url = (base_url or os.getenv("JIRA_BASE_URL", "")).rstrip("/")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")
        self.user_email = user_email or os.getenv("JIRA_USER_EMAIL", "")
        self.ingestion_service = DocumentIngestionService(session)

    async def ingest_issue(
        self,
        title: str,
        content: str,
        issue_key: str,
        status: str = "Resolved",
        author: str = "Jira Admin",
    ) -> tuple[Document, DocumentVersion]:
        doc_in = DocumentCreate(
            organization_id=self.organization_id,
            source_id=self.source_id,
            title=title.replace("\x00", "").strip(),
            content=content.replace("\x00", "").strip(),
            document_type="runbook",
            external_id=f"jira://{self.project_key}/{issue_key}",
            metadata={
                "project": self.project_key,
                "issue_key": issue_key,
                "status": status,
                "author": author,
                "connector": "jira",
            },
        )
        doc, version, _ = await self.ingestion_service.ingest_document(doc_in)
        return doc, version

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Syncs live operational rules and policies from Jira project."""
        if not self.base_url or not self.api_token or not self.user_email:
            raise RuntimeError(
                f"Jira live sync requires 'base_url', 'api_token', and 'user_email' for project '{self.project_key}'."
            )

        try:
            return await self._sync_live_jira()
        except Exception as e:
            raise RuntimeError(f"Jira sync failed for project '{self.project_key}': {str(e)}")

    async def _sync_live_jira(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        jql = f"project = {self.project_key} AND issuetype in (Standard, Policy, Runbook) ORDER BY updated DESC"
        url = f"{self.base_url}/rest/api/3/search?jql={jql}&maxResults=50"
        auth = (self.user_email, self.api_token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, auth=auth)
            if resp.status_code != 200:
                raise RuntimeError(f"Jira API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            for issue in data.get("issues", []):
                key = issue.get("key")
                fields = issue.get("fields", {})
                summary = fields.get("summary", f"Jira {key}")
                description = fields.get("description", "")
                desc_text = str(description) if description else ""
                content = f"# Jira Rule: {summary}\n\nKey: {key}\nStatus: {fields.get('status', {}).get('name', 'Active')}\n\n{desc_text}"
                res = await self.ingest_issue(
                    title=summary,
                    content=content,
                    issue_key=key,
                    status=fields.get("status", {}).get("name", "Active"),
                    author=fields.get("creator", {}).get("displayName", "Jira User"),
                )
                synced.append(res)
        return synced
