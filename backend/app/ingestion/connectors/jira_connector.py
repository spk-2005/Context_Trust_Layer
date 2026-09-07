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
    """Syncs release policies, operational runbooks, and incident rules from Atlassian Jira."""

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
        """Syncs operational rules and policies from Jira project."""
        if self.base_url and self.api_token and self.user_email:
            return await self._sync_live_jira()
        return await self._sync_simulated_jira()

    async def _sync_live_jira(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        jql = f"project = {self.project_key} AND issuetype in (Standard, Policy, Runbook) ORDER BY updated DESC"
        url = f"{self.base_url}/rest/api/3/search?jql={jql}&maxResults=50"
        auth = (self.user_email, self.api_token)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, auth=auth)
            if resp.status_code == 200:
                data = resp.json()
                for issue in data.get("issues", []):
                    key = issue.get("key")
                    fields = issue.get("fields", {})
                    summary = fields.get("summary", f"Jira {key}")
                    description = fields.get("description", "")
                    # Extract plain text if doc format
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

    async def _sync_simulated_jira(self) -> list[tuple[Document, DocumentVersion]]:
        # Realistic Jira operational runbook and SLA policies
        issues = [
            (
                "Production Incident Response SLA & Escalation Protocol",
                "# Sev-1 Outage SLA\n\nAll Sev-1 production incidents require initial response and executive escalation within 15 minutes.\n\n# Post-Mortem Requirements\n\nBlameless root cause analysis documents must be published within 72 hours of incident mitigation.",
                "OPS-402",
                "Active",
                "Site Reliability Engineering Team",
            ),
            (
                "Change Management & Friday Production Freeze Mandate",
                "# Production Deployment Protocol\n\nNo non-emergency production code deployments are permitted on Fridays after 14:00 UTC without Director sign-off.\n\n# Rollback Validation\n\nEvery automated deployment pipeline must have a verified one-click rollback script tested in staging.",
                "OPS-881",
                "Active",
                "DevOps Governance Board",
            ),
        ]
        synced = []
        for title, content, key, status, author in issues:
            res = await self.ingest_issue(title=title, content=content, issue_key=key, status=status, author=author)
            synced.append(res)
        return synced
