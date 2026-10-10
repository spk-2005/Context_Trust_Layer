import os
import uuid
from typing import Any, Sequence

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import EncryptionService
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.base import DiscoveredAsset, RawSourceAsset, SourceFamily, SyncMode
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate


class JiraConnector(BaseConnector):
    """Syncs live operational rules, issues, and policies from Atlassian Jira using genuine REST APIs."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        project_key: str = "OPS",
        base_url: str | None = None,
        api_token: str | None = None,
        user_email: str | None = None,
        owner_id: uuid.UUID | None = None,
        connection_config: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(session, organization_id, source_id, owner_id=owner_id)
        config = connection_config or {}
        self.project_key = (config.get("project_key") or project_key or "OPS").upper().strip()
        raw_url = config.get("base_url") or config.get("url") or config.get("jiraBaseUrl") or base_url or os.getenv("JIRA_BASE_URL", "")
        self.base_url = raw_url.rstrip("/") if raw_url else ""
        self.api_token = config.get("api_token") or config.get("token") or config.get("jiraToken") or api_token or kwargs.get("token") or kwargs.get("api_token") or os.getenv("JIRA_API_TOKEN", "")
        self.user_email = config.get("user_email") or config.get("email") or user_email or kwargs.get("email") or kwargs.get("user_email") or os.getenv("JIRA_USER_EMAIL", "")
        self.ingestion_service = DocumentIngestionService(session)

    async def test_connection(self) -> dict[str, Any]:
        """Verifies authentication, site reachability, and project access against live Jira REST API."""
        if not self.base_url:
            return {"success": False, "status": "error", "message": "Jira base URL is required."}
        if not self.user_email or not self.api_token:
            return {"success": False, "status": "error", "message": "Jira email and API token are required."}

        try:
            valid_url = EncryptionService.validate_external_url(self.base_url)
        except ValueError as err:
            return {"success": False, "status": "error", "message": f"Invalid Jira base URL: {str(err)}"}

        auth = (self.user_email.strip(), self.api_token.strip())
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Validator"}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                # 1. Verify user authentication
                user_resp = await client.get(f"{valid_url}/rest/api/3/myself", auth=auth, headers=headers)
                if user_resp.status_code == 401:
                    return {
                        "success": False,
                        "status": "error",
                        "message": "Jira authentication failed: Invalid user email or API token.",
                        "details": {"base_url": valid_url, "user_email": self.user_email},
                    }
                elif user_resp.status_code == 403:
                    return {
                        "success": False,
                        "status": "error",
                        "message": "Jira access forbidden: Account does not have API access permissions.",
                        "details": {"base_url": valid_url},
                    }
                elif user_resp.status_code != 200:
                    return {
                        "success": False,
                        "status": "error",
                        "message": f"Jira server responded with HTTP {user_resp.status_code}.",
                        "details": {"base_url": valid_url, "status_code": user_resp.status_code},
                    }

                user_data = user_resp.json()
                display_name = user_data.get("displayName", self.user_email)

                # 2. Verify project existence and access
                proj_resp = await client.get(f"{valid_url}/rest/api/3/project/{self.project_key}", auth=auth, headers=headers)
                if proj_resp.status_code == 404:
                    return {
                        "success": False,
                        "status": "error",
                        "message": f"Jira project '{self.project_key}' not found or access denied for user '{display_name}'.",
                        "details": {"project_key": self.project_key, "user": display_name},
                    }
                elif proj_resp.status_code != 200:
                    return {
                        "success": False,
                        "status": "error",
                        "message": f"Failed to access Jira project '{self.project_key}' (HTTP {proj_resp.status_code}).",
                        "details": {"project_key": self.project_key},
                    }

                proj_data = proj_resp.json()
                return {
                    "success": True,
                    "status": "ok",
                    "message": f"Successfully connected to Jira ({valid_url}) as '{display_name}'. Project '{proj_data.get('name', self.project_key)}' verified.",
                    "details": {
                        "base_url": valid_url,
                        "user": display_name,
                        "project_key": self.project_key,
                        "project_name": proj_data.get("name"),
                        "project_type": proj_data.get("projectTypeKey"),
                    },
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "status": "error",
                "message": f"Connection to Jira instance '{valid_url}' timed out (12s exceeded).",
                "details": {"base_url": valid_url},
            }
        except Exception as err:
            return {
                "success": False,
                "status": "error",
                "message": f"Jira connection error: {str(err)}",
                "details": {"base_url": valid_url},
            }

    @staticmethod
    async def discover_projects(base_url: str, user_email: str, api_token: str) -> list[dict[str, Any]]:
        """Discovers accessible projects on the target Jira instance."""
        if not base_url or not user_email or not api_token:
            return []
        try:
            valid_url = EncryptionService.validate_external_url(base_url.rstrip("/"))
            auth = (user_email.strip(), api_token.strip())
            headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Validator"}
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(f"{valid_url}/rest/api/3/project", auth=auth, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return [
                            {
                                "key": p.get("key"),
                                "name": p.get("name"),
                                "id": p.get("id"),
                                "project_type": p.get("projectTypeKey", "software"),
                            }
                            for p in data
                        ]
            return []
        except Exception:
            return []

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
            owner_id=self.owner_id,
            title=title.replace("\x00", "").strip(),
            content=content.replace("\x00", "").strip(),
            document_type="issue",
            external_id=f"jira://{self.project_key}/{issue_key}",
            metadata={
                "project": self.project_key,
                "issue_key": issue_key,
                "status": status,
                "author": author,
                "connector": "jira",
                "owner_id": str(self.owner_id) if self.owner_id else None,
            },
        )
        doc, version, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
        return doc, version

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Syncs live operational rules, tickets, and policies from Jira project."""
        if not self.base_url or not self.api_token or not self.user_email:
            raise RuntimeError(
                f"Jira Connector requires 'base_url', 'user_email', and 'api_token' for live synchronization. "
                f"Missing configuration for project '{self.project_key}'."
            )
        return await self._sync_live_jira()

    async def _sync_live_jira(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        valid_url = EncryptionService.validate_external_url(self.base_url)
        jql = f"project = \"{self.project_key}\" ORDER BY updated DESC"
        url = f"{valid_url}/rest/api/3/search?jql={jql}&maxResults=50"
        auth = (self.user_email.strip(), self.api_token.strip())
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Ingestion"}

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(url, auth=auth, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Jira API returned HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            issues = data.get("issues", [])
            for issue in issues:
                key = issue.get("key")
                fields = issue.get("fields", {})
                summary = fields.get("summary", f"Jira {key}")
                status_name = fields.get("status", {}).get("name", "Active")
                creator_name = fields.get("creator", {}).get("displayName", "Jira User")

                # Handle Atlassian Document Format (ADF) or string description
                raw_desc = fields.get("description", "")
                desc_text = self._extract_adf_text(raw_desc)

                content = (
                    f"# Jira Issue: {summary}\n\n"
                    f"**Key**: `{key}` | **Status**: `{status_name}` | **Project**: `{self.project_key}`\n\n"
                    f"**Reporter/Creator**: {creator_name}\n\n"
                    f"## Description & Policy Details\n\n{desc_text or 'No description provided.'}"
                )
                res = await self.ingest_issue(
                    title=f"[{key}] {summary}",
                    content=content,
                    issue_key=key,
                    status=status_name,
                    author=creator_name,
                )
                synced.append(res)

        return synced

    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Discovers Jira projects and active issue types as DiscoveredAssets."""
        assets: list[DiscoveredAsset] = []
        if not self.base_url or not self.user_email or not self.api_token:
            return assets

        url = f"{self.base_url}/rest/api/3/project/{self.project_key}"
        auth = (self.user_email, self.api_token)
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Discovery"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, auth=auth, headers=headers)
                if resp.status_code == 200:
                    proj = resp.json()
                    assets.append(
                        DiscoveredAsset(
                            asset_id=f"jira://{self.project_key}",
                            name=f"{proj.get('name', self.project_key)} ({self.project_key})",
                            asset_type="project",
                            source_family=SourceFamily.CONVERSATION,
                            metadata={"project_key": self.project_key, "project_id": proj.get("id")},
                        )
                    )
                    for itype in proj.get("issueTypes", []):
                        assets.append(
                            DiscoveredAsset(
                                asset_id=f"jira://{self.project_key}/type/{itype.get('id')}",
                                name=itype.get("name", "Issue Type"),
                                asset_type="issue_type",
                                source_family=SourceFamily.CONVERSATION,
                                parent_id=f"jira://{self.project_key}",
                                metadata={"type_id": itype.get("id"), "subtask": itype.get("subtask")},
                            )
                        )
            except Exception:
                pass
        return assets

    async def fetch_native_assets(
        self,
        selected_asset_ids: list[str] | None = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: dict[str, Any] | None = None,
    ) -> list[RawSourceAsset]:
        """Fetches native Jira issues with full author, timestamps, status transitions, and fields."""
        native_assets: list[RawSourceAsset] = []
        if not self.base_url or not self.user_email or not self.api_token:
            return native_assets

        jql = f"project = '{self.project_key}' ORDER BY updated DESC"
        url = f"{self.base_url}/rest/api/3/search?jql={httpx.URL('', params={'q': jql}).query.decode()[2:]}&maxResults=50"
        auth = (self.user_email, self.api_token)
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Ingestion"}

        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                resp = await client.get(url, auth=auth, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for issue in data.get("issues", []):
                        key = issue.get("key")
                        asset_id = f"jira://{self.project_key}/issue/{key}"
                        if selected_asset_ids and asset_id not in selected_asset_ids:
                            continue

                        fields = issue.get("fields", {})
                        native_assets.append(
                            RawSourceAsset(
                                asset_id=asset_id,
                                source_family=SourceFamily.CONVERSATION,
                                native_format="jira_issue",
                                source_version=str(fields.get("updated") or "1"),
                                raw_payload=issue,
                                locator_metadata={
                                    "project_key": self.project_key,
                                    "issue_key": key,
                                    "status": fields.get("status", {}).get("name"),
                                    "author": fields.get("creator", {}).get("displayName"),
                                },
                            )
                        )
            except Exception:
                pass
        return native_assets

    def _extract_adf_text(self, adf_node: Any) -> str:
        """Recursively extracts plain text from Atlassian Document Format structure."""
        if not adf_node:
            return ""
        if isinstance(adf_node, str):
            return adf_node
        if isinstance(adf_node, dict):
            text_parts = []
            if "text" in adf_node:
                text_parts.append(adf_node["text"])
            for child in adf_node.get("content", []):
                child_text = self._extract_adf_text(child)
                if child_text:
                    text_parts.append(child_text)
            return "\n".join(text_parts) if adf_node.get("type") in ("paragraph", "heading") else " ".join(text_parts)
        if isinstance(adf_node, list):
            return "\n".join(self._extract_adf_text(item) for item in adf_node)
        return str(adf_node)

