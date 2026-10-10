import base64
import os
import uuid
from typing import Any, Sequence

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceFamily, SourceIntent
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.base import DiscoveredAsset, RawSourceAsset, SyncMode
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate


def sanitize_github_repo(repo: str) -> str:
    """Sanitizes raw GitHub inputs (HTTPS URLs, SSH clone URLs, .git suffix) into 'owner/repo' format."""
    if not repo:
        return "demo-org/security-standards"
    r = repo.strip()
    if r.startswith("git@github.com:"):
        r = r[len("git@github.com:"):]
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if r.startswith(prefix):
            r = r[len(prefix):]
    r = r.strip("/")
    if r.endswith(".git"):
        r = r[:-4]
    parts = [p for p in r.split("/") if p]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return r or "demo-org/security-standards"


class GitHubConnector(BaseConnector):
    """Syncs live markdown policies, architecture guides, and repository documentation directly from GitHub.
    
    Features rate-limit immunity via Git Trees single-call indexing, Raw GitHub CDN fast-fetching,
    and automatic candidate fallback probing for governance/policy documents.
    """

    # Common policy/governance paths probed when unauthenticated rate limits hit api.github.com
    COMMON_PROBE_PATHS = [
        "docs/secops_mandate_v2.md",
        "docs/secops_mandate_v1.md",
        "docs/api_deprecation_policy_v1_2.md",
        "README.md",
        "readme.md",
        "docs/security_policy.md",
        "docs/security.md",
        "docs/architecture.md",
        "docs/governance.md",
        "policies/security_policy.md",
        "policies/compliance.md",
        "SECURITY.md",
    ]

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        repo: str = "demo-org/security-standards",
        branch: str | None = None,
        token: str | None = None,
        paths: list[str] | None = None,
        owner_id: uuid.UUID | None = None,
        scope_config: dict[str, Any] | None = None,
        source_intent: SourceIntent | None = None,
        **kwargs,
    ):
        super().__init__(
            session,
            organization_id,
            source_id,
            owner_id=owner_id,
            scope_config=scope_config,
            source_intent=source_intent,
        )
        self.repo = sanitize_github_repo(repo)
        self.branch = branch.strip() if branch and branch.strip() else None
        self.token = (token or os.getenv("GITHUB_TOKEN", "")).strip()
        self.paths = paths or ["", "docs", "policies", ".github"]
        self.ingestion_service = DocumentIngestionService(session)

    @property
    def source_family(self) -> SourceFamily:
        return SourceFamily.DOCUMENT

    @property
    def source_intent(self) -> SourceIntent:
        return self._source_intent or SourceIntent.GOVERNANCE_POLICY

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
            "pagination_type": "none",
            "native_identifier_field": "commit_sha",
        }

    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Layer 2 discovery: Discovers selectable files in the repository."""
        assets = []
        clean_repo = sanitize_github_repo(self.repo)
        active_branch = self.branch or "main"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Context-Trust-Layer-Validator",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}" if not self.token.startswith(("Bearer ", "token ")) else self.token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                trees_url = f"https://api.github.com/repos/{clean_repo}/git/trees/{active_branch}?recursive=1"
                resp = await client.get(trees_url, headers=headers)
                if resp.status_code == 200:
                    tree_data = resp.json().get("tree", [])
                    for it in tree_data:
                        path = it.get("path", "")
                        if it.get("type") == "blob" and path.lower().endswith((".md", ".txt", ".json", ".yaml", ".yml")):
                            assets.append(
                                DiscoveredAsset(
                                    id=path,
                                    asset_id=path,
                                    name=path.split("/")[-1],
                                    asset_type="file",
                                    source_family=SourceFamily.DOCUMENT,
                                    parent_scope=path.rsplit("/", 1)[0] if "/" in path else "",
                                    is_selectable=True,
                                    metadata={"path": path, "sha": it.get("sha"), "size": it.get("size")},
                                )
                            )
        except Exception:
            pass

        if not assets:
            for p in self.COMMON_PROBE_PATHS:
                assets.append(
                    DiscoveredAsset(
                        id=p,
                        asset_id=p,
                        name=p.split("/")[-1],
                        asset_type="file",
                        source_family=SourceFamily.DOCUMENT,
                        parent_scope=p.rsplit("/", 1)[0] if "/" in p else "",
                        is_selectable=True,
                        metadata={"path": p, "probe_candidate": True},
                    )
                )

        return assets

    async def test_connection(self) -> dict[str, Any]:
        """Authenticates and verifies access to the configured GitHub repository."""
        clean_repo = sanitize_github_repo(self.repo)
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Context-Trust-Layer-Validator",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}" if not self.token.startswith(("Bearer ", "token ")) else self.token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://api.github.com/repos/{clean_repo}", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    default_branch = data.get("default_branch", self.branch or "main")
                    is_private = data.get("private", False)
                    return {
                        "success": True,
                        "status": "ok",
                        "message": f"Successfully authenticated and verified repository '{clean_repo}' ({'private' if is_private else 'public'}, default branch: {default_branch}).",
                        "details": {
                            "repo": clean_repo,
                            "default_branch": default_branch,
                            "is_private": is_private,
                            "stars": data.get("stargazers_count", 0),
                            "auth_mode": "authenticated" if self.token else "public",
                        },
                    }
                elif resp.status_code == 401:
                    return {
                        "success": False,
                        "status": "error",
                        "message": "GitHub authentication failed: Personal Access Token is invalid or expired.",
                        "details": {"repo": clean_repo},
                    }
                elif resp.status_code == 404:
                    # Check if unauthenticated raw readme works
                    raw_check = await client.get(f"https://raw.githubusercontent.com/{clean_repo}/{self.branch or 'main'}/README.md")
                    if raw_check.status_code == 200:
                        return {
                            "success": True,
                            "status": "ok",
                            "message": f"Verified public repository '{clean_repo}' via raw access.",
                            "details": {"repo": clean_repo, "branch": self.branch or "main"},
                        }
                    return {
                        "success": False,
                        "status": "error",
                        "message": f"GitHub repository '{clean_repo}' not found. Verify repository name and ensure token has repo access.",
                        "details": {"repo": clean_repo},
                    }
                elif resp.status_code in (403, 429):
                    # Rate limit encountered
                    raw_check = await client.get(f"https://raw.githubusercontent.com/{clean_repo}/{self.branch or 'main'}/README.md")
                    if raw_check.status_code == 200:
                        return {
                            "success": True,
                            "status": "warning",
                            "message": f"Repository '{clean_repo}' verified via CDN (API rate-limited). Provide Personal Access Token for full API features.",
                            "details": {"repo": clean_repo},
                        }
                    return {
                        "success": False,
                        "status": "error",
                        "message": "GitHub API rate limit exceeded. Please configure a valid Personal Access Token.",
                        "details": {"repo": clean_repo},
                    }
                else:
                    return {
                        "success": False,
                        "status": "error",
                        "message": f"GitHub API returned HTTP {resp.status_code}: {resp.text[:200]}",
                        "details": {"repo": clean_repo, "status_code": resp.status_code},
                    }
        except httpx.TimeoutException:
            return {
                "success": False,
                "status": "error",
                "message": "Connection to GitHub API timed out (10s limit exceeded).",
                "details": {"repo": clean_repo},
            }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "message": f"GitHub connection error: {str(e)}",
                "details": {"repo": clean_repo},
            }

    @staticmethod
    async def discover_repositories(token: str | None = None, owner: str | None = None) -> list[dict[str, Any]]:
        """Discovers accessible repositories via GitHub API."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Context-Trust-Layer-Validator",
        }
        if token:
            clean_token = token.strip()
            headers["Authorization"] = f"Bearer {clean_token}" if not clean_token.startswith(("Bearer ", "token ")) else clean_token

        async with httpx.AsyncClient(timeout=12.0) as client:
            if owner and owner.strip():
                clean_owner = owner.strip()
                # Try org repos first then user repos
                url = f"https://api.github.com/orgs/{clean_owner}/repos?per_page=50&sort=updated"
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    url = f"https://api.github.com/users/{clean_owner}/repos?per_page=50&sort=updated"
                    resp = await client.get(url, headers=headers)
            else:
                url = "https://api.github.com/user/repos?per_page=50&sort=updated" if token else ""

            if not url:
                return []

            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                repos = resp.json()
                if isinstance(repos, list):
                    return [
                        {
                            "name": r.get("name"),
                            "full_name": r.get("full_name"),
                            "default_branch": r.get("default_branch", "main"),
                            "private": r.get("private", False),
                            "description": r.get("description", ""),
                        }
                        for r in repos
                    ]
            return []

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
            owner_id=self.owner_id,
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
                "owner_id": str(self.owner_id) if self.owner_id else None,
            },
        )
        doc, version, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
        return doc, version

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Syncs live markdown documentation and security guidelines from GitHub repository."""
        try:
            return await self._sync_github()
        except Exception as err:
            raise RuntimeError(f"GitHub Sync Failed for '{self.repo}': {str(err)}")

    async def _sync_github(self) -> list[tuple[Document, DocumentVersion]]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Context-Trust-Layer-Ingestion-Bot",
        }
        if self.token:
            auth_header = f"Bearer {self.token}" if not self.token.startswith(("Bearer ", "token ")) else self.token
            headers["Authorization"] = auth_header

        async with httpx.AsyncClient(timeout=25.0) as client:
            # 1. Inspect repository metadata
            repo_url = f"https://api.github.com/repos/{self.repo}"
            repo_resp = await client.get(repo_url, headers=headers)
            
            is_rate_limited = repo_resp.status_code in (401, 403, 429)
            
            if repo_resp.status_code == 404:
                # Could be private without valid token, or not found.
                # Try raw probe on default branches before failing.
                probed = await self._probe_raw_candidates(client, branches=["main", "master"])
                if probed:
                    return probed
                raise RuntimeError(
                    f"GitHub repository '{self.repo}' not found. Make sure repository exists and is public, or provide a GITHUB_TOKEN."
                )

            active_branch = self.branch
            repo_info = {}

            if repo_resp.status_code == 200:
                raw_data = repo_resp.json()
                if isinstance(raw_data, dict):
                    repo_info = raw_data
                    if not active_branch:
                        active_branch = repo_info.get("default_branch", "main")
            
            if not active_branch:
                active_branch = "main"
            self.branch = active_branch

            # 2. Try single-call Git Trees API if not rate limited
            synced = []
            if not is_rate_limited:
                tree_url = f"https://api.github.com/repos/{self.repo}/git/trees/{active_branch}?recursive=1"
                tree_resp = await client.get(tree_url, headers=headers)
                
                if tree_resp.status_code == 200:
                    tree_data = tree_resp.json()
                    items = tree_data.get("tree", []) if isinstance(tree_data, dict) else []
                    
                    # Filter for documentation, markdown, and governance files
                    doc_items = [
                        it for it in items
                        if it.get("type") == "blob"
                        and it.get("path", "").lower().endswith((".md", ".txt", ".yaml", ".yml", ".json"))
                        and not it.get("path", "").lower().endswith(("package-lock.json", ".min.json", "tsconfig.tsbuildinfo"))
                        and not any(ignored in it.get("path", "").lower() for ignored in ("node_modules/", ".git/", "vendor/"))
                    ]

                    # Prioritize docs/, policies/, and markdown files
                    doc_items.sort(
                        key=lambda x: (
                            0 if any(p in x.get("path", "").lower() for p in ("docs/", "policies/", "mandate", "secops", "governance"))
                            else 1 if x.get("path", "").lower().endswith(".md")
                            else 2
                        )
                    )

                    # Ingest matching documentation files (capped to 50 files per sync for performance)
                    for item in doc_items[:50]:
                        path = item.get("path")
                        file_sha = item.get("sha", "latest")
                        
                        # Download raw content using Raw CDN (0 API quota consumption!)
                        raw_url = f"https://raw.githubusercontent.com/{self.repo}/{active_branch}/{path}"
                        raw_resp = await client.get(raw_url, headers={"User-Agent": "Context-Trust-Layer-Bot"})
                        
                        if raw_resp.status_code == 200:
                            content = raw_resp.text
                            clean_name = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
                            res = await self.ingest_markdown(
                                title=clean_name,
                                content=content,
                                file_path=path,
                                commit_sha=file_sha,
                            )
                            synced.append(res)

                    if synced:
                        return synced

            # 3. Fallback: If Trees API was rate-limited (403/429) or yielded 0 items, probe raw GitHub CDN
            probed = await self._probe_raw_candidates(client, branches=[active_branch, "main", "master"])
            if probed:
                return probed

            # 4. If repository was reachable but had no markdown docs, create a repository overview
            if repo_info or not is_rate_limited:
                desc = repo_info.get("description") or "Live connected repository"
                stars = repo_info.get("stargazers_count", 0)
                lang = repo_info.get("language") or "Code"
                overview_text = (
                    f"# GitHub Repository: {self.repo}\n\n"
                    f"Branch: `{active_branch}`\n"
                    f"Primary Language: {lang}\n"
                    f"Description: {desc}\n"
                    f"Stars: {stars}\n\n"
                    f"Connected to Context Trust Gate."
                )
                res = await self.ingest_markdown(
                    title=f"{self.repo.split('/')[-1]} Repository Overview",
                    content=overview_text,
                    file_path="REPO_OVERVIEW.md",
                    commit_sha="HEAD",
                )
                return [res]

            # If all avenues were rate limited and no files could be probed:
            raise RuntimeError(
                f"GitHub API rate limit exceeded for repository '{self.repo}'. "
                f"Please configure a GitHub Personal Access Token (GITHUB_TOKEN) in settings or connector configuration."
            )

    async def _probe_raw_candidates(
        self,
        client: httpx.AsyncClient,
        branches: list[str],
    ) -> list[tuple[Document, DocumentVersion]]:
        """Probes known candidate policy and documentation files directly against the raw GitHub CDN."""
        synced = []
        seen_paths = set()
        
        for branch in dict.fromkeys(b for b in branches if b):
            for candidate in self.COMMON_PROBE_PATHS:
                if candidate in seen_paths:
                    continue
                raw_url = f"https://raw.githubusercontent.com/{self.repo}/{branch}/{candidate}"
                try:
                    resp = await client.get(raw_url, headers={"User-Agent": "Context-Trust-Layer-Bot"})
                    if resp.status_code == 200 and resp.text.strip():
                        seen_paths.add(candidate)
                        clean_name = candidate.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
                        res = await self.ingest_markdown(
                            title=clean_name,
                            content=resp.text,
                            file_path=candidate,
                            commit_sha="raw-cdn-head",
                        )
                        synced.append(res)
                except Exception:
                    continue
    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Discovers markdown policies, documentation, and configuration files in the target repository."""
        assets: list[DiscoveredAsset] = []
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Context-Trust-Layer-App"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        api_base = "https://api.github.com"
        branch = self.branch or "main"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                tree_url = f"{api_base}/repos/{self.repo}/git/trees/{branch}?recursive=1"
                resp = await client.get(tree_url, headers=headers)
                if resp.status_code == 200:
                    tree_data = resp.json().get("tree", [])
                    for item in tree_data:
                        path = item.get("path", "")
                        if item.get("type") == "blob" and (path.endswith(".md") or path.endswith(".markdown") or path.endswith(".json")):
                            assets.append(
                                DiscoveredAsset(
                                    asset_id=f"github://{self.repo}/{branch}/{path}",
                                    name=path,
                                    asset_type="file",
                                    source_family=SourceFamily.DOCUMENT if path.endswith((".md", ".markdown")) else SourceFamily.STRUCTURED,
                                    parent_id=f"github://{self.repo}/{branch}",
                                    metadata={
                                        "repository": self.repo,
                                        "branch": branch,
                                        "path": path,
                                        "sha": item.get("sha"),
                                        "size": item.get("size"),
                                    },
                                )
                            )
                else:
                    # Fallback candidate probe
                    for candidate in self.COMMON_PROBE_PATHS:
                        assets.append(
                            DiscoveredAsset(
                                asset_id=f"github://{self.repo}/{branch}/{candidate}",
                                name=candidate,
                                asset_type="file",
                                source_family=SourceFamily.DOCUMENT,
                                parent_id=f"github://{self.repo}/{branch}",
                                metadata={"repository": self.repo, "branch": branch, "path": candidate},
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
        """Fetches raw markdown content, commit SHAs, and file coordinates without loss of structure."""
        native_assets: list[RawSourceAsset] = []
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Context-Trust-Layer-App"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        api_base = "https://api.github.com"
        branch = self.branch or "main"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 1. Fetch latest commit SHA
                commit_sha = "HEAD"
                try:
                    c_resp = await client.get(f"{api_base}/repos/{self.repo}/commits/{branch}", headers=headers)
                    if c_resp.status_code == 200:
                        commit_sha = c_resp.json().get("sha", "HEAD")[:12]
                except Exception:
                    pass

                # 2. Get discovered files
                discovered = await self.discover_assets()
                for asset in discovered:
                    # Robust scope matching: matches exact asset_id, repo URL, path prefix, or wildcard
                    if selected_asset_ids and "*" not in selected_asset_ids:
                        matched = False
                        for sel in selected_asset_ids:
                            sel_clean = (sel or "").strip().rstrip("/")
                            if not sel_clean:
                                continue
                            if (
                                sel_clean == asset.asset_id
                                or sel_clean in (asset.asset_id or "")
                                or sanitize_github_repo(sel_clean) == self.repo
                                or (asset.metadata.get("path") and sel_clean.endswith(asset.metadata["path"]))
                            ):
                                matched = True
                                break
                        if not matched:
                            continue

                    path = asset.metadata.get("path") or asset.asset_id or asset.id or asset.name
                    raw_url = f"https://raw.githubusercontent.com/{self.repo}/{branch}/{path}"
                    raw_headers = {"User-Agent": "Context-Trust-Layer-Bot"}
                    if self.token:
                        raw_headers["Authorization"] = f"token {self.token}"

                    try:
                        resp = await client.get(raw_url, headers=raw_headers)
                        if resp.status_code == 200 and resp.text.strip():
                            native_assets.append(
                                RawSourceAsset(
                                    asset_id=asset.asset_id or asset.id or f"github://{self.repo}/{branch}/{path}",
                                    source_family=asset.source_family,
                                    native_format="markdown" if path.endswith((".md", ".markdown")) else "json",
                                    source_version=commit_sha,
                                    raw_payload=resp.text,
                                    locator_metadata={
                                        "repository": self.repo,
                                        "branch": branch,
                                        "path": path,
                                        "commit_sha": commit_sha,
                                    },
                                )
                            )
                    except Exception:
                        continue
            except Exception:
                pass
        return native_assets

