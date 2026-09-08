import base64
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


class GitHubConnector(BaseConnector):
    """Syncs live markdown policies, architecture guides, and repository documentation directly from GitHub."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        repo: str = "acme-corp/security-standards",
        branch: str | None = None,
        token: str | None = None,
        paths: list[str] | None = None,
    ):
        super().__init__(session, organization_id, source_id)
        clean_repo = (repo or "").replace("https://github.com/", "").replace("http://github.com/", "").strip("/")
        self.repo = clean_repo or "acme-corp/security-standards"
        self.branch = branch
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.paths = paths or ["", "docs", "policies", ".github"]
        self.ingestion_service = DocumentIngestionService(session)

    async def ingest_markdown(
        self,
        title: str,
        content: str,
        file_path: str,
        commit_sha: str = "HEAD",
        author: str = "GitHub Contributor",
    ) -> tuple[Document, DocumentVersion]:
        doc_in = DocumentCreate(
            organization_id=self.organization_id,
            source_id=self.source_id,
            title=title.replace("\x00", "").strip(),
            content=content.replace("\x00", "").strip(),
            document_type="policy",
            external_id=f"github://{self.repo}/{file_path}",
            metadata={
                "repo": self.repo,
                "branch": self.branch or "default",
                "file_path": file_path,
                "commit_sha": commit_sha,
                "author": author,
                "connector": "github",
            },
        )
        doc, version, _ = await self.ingestion_service.ingest_document(doc_in)
        return doc, version

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Syncs live markdown documentation and security guidelines from GitHub repository."""
        try:
            return await self._sync_live_github()
        except Exception as err:
            raise RuntimeError(f"GitHub Sync Failed for '{self.repo}': {str(err)}")

    async def _sync_live_github(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Context-Trust-Layer-Ingestion-Bot",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=25.0) as client:
            repo_url = f"https://api.github.com/repos/{self.repo}"
            repo_resp = await client.get(repo_url, headers=headers)
            if repo_resp.status_code == 404:
                raise RuntimeError(f"GitHub repository '{self.repo}' not found. Make sure repository exists and is public, or provide a GITHUB_TOKEN.")
            elif repo_resp.status_code in (401, 403):
                msg = repo_resp.json().get("message", "Authentication required or rate limited")
                raise RuntimeError(f"GitHub API Error: {msg}")

            repo_info = repo_resp.json() if repo_resp.status_code == 200 else {}
            active_branch = self.branch or repo_info.get("default_branch", "main")
            self.branch = active_branch

            fetched_paths = set()
            for subpath in self.paths:
                clean_path = subpath.strip("/")
                url = f"https://api.github.com/repos/{self.repo}/contents/{clean_path}?ref={active_branch}"
                resp = await client.get(url, headers=headers)

                if resp.status_code != 200:
                    continue

                items = resp.json()
                if isinstance(items, dict):
                    items = [items]

                for item in items:
                    path = item.get("path")
                    if path in fetched_paths:
                        continue

                    name_lower = item.get("name", "").lower()
                    if item.get("type") == "file" and name_lower.endswith((".md", ".txt", ".json", ".yaml", ".yml")):
                        file_url = item.get("url")
                        file_resp = await client.get(file_url, headers=headers)
                        if file_resp.status_code == 200:
                            file_data = file_resp.json()
                            content_b64 = file_data.get("content", "")
                            raw_text = base64.b64decode(content_b64).decode("utf-8", errors="replace")
                            name = item.get("name", "").rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
                            res = await self.ingest_markdown(
                                title=name,
                                content=raw_text,
                                file_path=path,
                                commit_sha=file_data.get("sha", "latest"),
                            )
                            synced.append(res)
                            fetched_paths.add(path)

            if not synced:
                desc = repo_info.get("description") or "Live connected repository"
                stars = repo_info.get("stargazers_count", 0)
                lang = repo_info.get("language") or "Code"
                overview_text = f"# GitHub Repository: {self.repo}\n\nBranch: `{active_branch}`\nPrimary Language: {lang}\nDescription: {desc}\nStars: {stars}\n\nConnected to Context Trust Gate."
                res = await self.ingest_markdown(
                    title=f"{self.repo.split('/')[-1]} Repository Overview",
                    content=overview_text,
                    file_path="REPO_OVERVIEW.md",
                    commit_sha="HEAD",
                )
                synced.append(res)

        return synced
