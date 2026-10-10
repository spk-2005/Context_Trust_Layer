import html
import os
import re
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


def _html_to_markdown(html_content: str) -> str:
    """Converts Confluence storage format HTML into clean readable Markdown."""
    if not html_content:
        return ""
    text = html_content
    # Replace headers
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h4[^>]*>(.*?)</h4>", r"#### \1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    # Replace list items
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    # Replace paragraphs and line breaks
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", r"\n", text, flags=re.IGNORECASE)
    # Strip any remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Collapse excess whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class ConfluenceConnector(BaseConnector):
    """Syncs documents, SOPs, and policies from Atlassian Confluence spaces using genuine REST APIs."""

    @classmethod
    def _normalize_base_url(cls, raw_url: str | None) -> str:
        """Strips trailing slashes and /wiki suffix to ensure canonical base URL for Confluence Cloud API."""
        if not raw_url:
            return ""
        url = raw_url.strip().rstrip("/")
        if url.endswith("/wiki"):
            url = url[:-5].rstrip("/")
        return url

    @classmethod
    def _parse_space_keys(cls, raw_spaces: Any) -> list[str]:
        """Parses comma-separated string or list of space keys, stripping whitespace and removing empty items."""
        if not raw_spaces:
            return ["POLICIES"]
        if isinstance(raw_spaces, list):
            keys = []
            for item in raw_spaces:
                keys.extend(cls._parse_space_keys(item))
            seen = set()
            dedup = []
            for k in keys:
                if k not in seen:
                    seen.add(k)
                    dedup.append(k)
            return dedup if dedup else ["POLICIES"]

        val = str(raw_spaces).strip()
        if val.startswith("confluence://"):
            val = val[len("confluence://"):].split("/")[0]
        parts = [p.strip().upper() for p in val.split(",") if p.strip()]
        seen = set()
        dedup = []
        for p in parts:
            if p not in seen:
                seen.add(p)
                dedup.append(p)
        return dedup if dedup else ["POLICIES"]

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        space_key: str = "POLICIES",
        base_url: str | None = None,
        api_token: str | None = None,
        user_email: str | None = None,
        owner_id: uuid.UUID | None = None,
        connection_config: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(session, organization_id, source_id, owner_id=owner_id)
        config = connection_config or {}
        raw_space = config.get("space_keys") or config.get("space_key") or config.get("spaces") or space_key or "POLICIES"
        self.space_keys = self._parse_space_keys(raw_space)
        self.space_key = self.space_keys[0] if self.space_keys else "POLICIES"
        raw_url = config.get("base_url") or config.get("url") or config.get("confluenceBaseUrl") or base_url or os.getenv("CONFLUENCE_BASE_URL", "")
        self.base_url = self._normalize_base_url(raw_url)
        self.api_token = config.get("api_token") or config.get("token") or config.get("confluenceToken") or api_token or kwargs.get("token") or kwargs.get("api_token") or os.getenv("CONFLUENCE_API_TOKEN", "")
        self.user_email = config.get("user_email") or config.get("email") or user_email or kwargs.get("email") or kwargs.get("user_email") or os.getenv("CONFLUENCE_USER_EMAIL", "")
        self.ingestion_service = DocumentIngestionService(session)

    async def test_connection(self) -> dict[str, Any]:
        """Verifies authentication, site reachability, and space access against live Confluence REST API across target spaces."""
        if not self.base_url:
            return {"success": False, "status": "error", "message": "Confluence base URL is required."}
        if not self.user_email or not self.api_token:
            return {"success": False, "status": "error", "message": "Confluence user email and API token are required."}

        try:
            valid_url = self._normalize_base_url(EncryptionService.validate_external_url(self.base_url))
        except ValueError as err:
            return {"success": False, "status": "error", "message": f"Invalid Confluence base URL: {str(err)}"}

        auth = (self.user_email.strip(), self.api_token.strip())
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Validator"}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                # 1. Verify user authentication
                user_resp = await client.get(f"{valid_url}/wiki/rest/api/user/current", auth=auth, headers=headers)
                if user_resp.status_code == 401:
                    return {
                        "success": False,
                        "status": "error",
                        "message": "Confluence authentication failed: Invalid email or API token.",
                        "details": {"base_url": valid_url},
                    }
                elif user_resp.status_code == 403:
                    return {
                        "success": False,
                        "status": "error",
                        "message": "Confluence access forbidden: Insufficient permissions for API access.",
                        "details": {"base_url": valid_url},
                    }

                # 2. Verify all target spaces individually
                verified_spaces: list[dict[str, Any]] = []
                missing_spaces: list[str] = []
                failed_spaces: list[str] = []

                for sp in self.space_keys:
                    space_resp = await client.get(f"{valid_url}/wiki/rest/api/space/{sp}", auth=auth, headers=headers)
                    if space_resp.status_code == 200:
                        space_data = space_resp.json()
                        verified_spaces.append({
                            "key": sp,
                            "name": space_data.get("name", sp),
                            "type": space_data.get("type", "global"),
                        })
                    elif space_resp.status_code == 404:
                        missing_spaces.append(sp)
                    else:
                        failed_spaces.append(f"{sp} (HTTP {space_resp.status_code})")

                # If none of the spaces were found
                if missing_spaces and not verified_spaces:
                    return {
                        "success": False,
                        "status": "error",
                        "message": f"Confluence space(s) '{', '.join(missing_spaces)}' not found or inaccessible for this account.",
                        "details": {"space_keys": self.space_keys, "missing": missing_spaces},
                    }

                if not verified_spaces:
                    return {
                        "success": False,
                        "status": "error",
                        "message": f"Failed to access Confluence spaces: {', '.join(failed_spaces)}.",
                        "details": {"space_keys": self.space_keys, "failed": failed_spaces},
                    }

                # If some spaces were missing but at least one verified: keep verified spaces
                if missing_spaces:
                    self.space_keys = [v["key"] for v in verified_spaces]
                    self.space_key = self.space_keys[0]
                    verified_keys = ", ".join(v["key"] for v in verified_spaces)
                    missing_str = ", ".join(missing_spaces)
                    return {
                        "success": True,
                        "status": "ok",
                        "message": f"Successfully connected to Confluence ({valid_url}). Verified space(s): {verified_keys}. (Notice: Space(s) '{missing_str}' not found and will be skipped).",
                        "details": {
                            "base_url": valid_url,
                            "space_key": self.space_key,
                            "space_keys": self.space_keys,
                            "verified": verified_spaces,
                            "excluded_spaces": missing_spaces,
                        },
                    }

                # All specified spaces verified
                verified_keys = ", ".join(v["key"] for v in verified_spaces)
                return {
                    "success": True,
                    "status": "ok",
                    "message": f"Successfully connected to Confluence ({valid_url}). Verified {len(verified_spaces)} space(s): {verified_keys}.",
                    "details": {
                        "base_url": valid_url,
                        "space_key": self.space_key,
                        "space_keys": self.space_keys,
                        "verified": verified_spaces,
                    },
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "status": "error",
                "message": f"Connection to Confluence '{valid_url}' timed out (12s exceeded).",
                "details": {"base_url": valid_url},
            }
        except Exception as err:
            return {
                "success": False,
                "status": "error",
                "message": f"Confluence connection error: {str(err)}",
                "details": {"base_url": valid_url},
            }

    @classmethod
    async def discover_spaces(cls, base_url: str, user_email: str, api_token: str) -> list[dict[str, Any]]:
        """Discovers accessible spaces on the target Confluence instance."""
        if not base_url or not user_email or not api_token:
            return []
        try:
            valid_url = cls._normalize_base_url(EncryptionService.validate_external_url(base_url.rstrip("/")))
            auth = (user_email.strip(), api_token.strip())
            headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Validator"}
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(f"{valid_url}/wiki/rest/api/space?limit=50", auth=auth, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    return [
                        {
                            "key": s.get("key"),
                            "name": s.get("name"),
                            "type": s.get("type", "global"),
                            "id": s.get("id"),
                        }
                        for s in results
                    ]
            return []
        except Exception:
            return []

    async def ingest_page(
        self,
        title: str,
        content: str,
        page_id: str,
        version_num: int = 1,
        author: str = "Confluence Author",
        space_key: str | None = None,
    ) -> tuple[Document, DocumentVersion]:
        effective_space = (space_key or self.space_key or "POLICIES").upper().strip()
        doc_in = DocumentCreate(
            organization_id=self.organization_id,
            source_id=self.source_id,
            owner_id=self.owner_id,
            title=title.replace("\x00", "").strip(),
            content=content.replace("\x00", "").strip(),
            document_type="confluence_page",
            external_id=f"confluence://{effective_space}/{page_id}",
            metadata={
                "space": effective_space,
                "author": author,
                "upstream_version": version_num,
                "connector": "confluence",
                "owner_id": str(self.owner_id) if self.owner_id else None,
            },
        )
        doc, version, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
        return doc, version

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Syncs live pages from Confluence using REST API across all configured spaces."""
        if not self.base_url or not self.api_token or not self.user_email:
            raise RuntimeError(
                f"Confluence Connector requires 'base_url', 'user_email', and 'api_token' for live synchronization. "
                f"Missing configuration for space(s) '{', '.join(self.space_keys)}'."
            )
        return await self._sync_live_confluence()

    async def _sync_live_confluence(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        valid_url = self._normalize_base_url(EncryptionService.validate_external_url(self.base_url))
        auth = (self.user_email.strip(), self.api_token.strip())
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Ingestion"}

        async with httpx.AsyncClient(timeout=25.0) as client:
            for sp in self.space_keys:
                url = f"{valid_url}/wiki/rest/api/content?spaceKey={sp}&expand=body.storage,version,history&limit=50"
                resp = await client.get(url, auth=auth, headers=headers)
                if resp.status_code == 404:
                    # Space not found or empty, continue to next space
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(f"Confluence API returned HTTP {resp.status_code} for space '{sp}': {resp.text[:200]}")

                data = resp.json()
                for item in data.get("results", []):
                    pid = str(item.get("id"))
                    title = item.get("title", f"Confluence Page {pid}")
                    body_html = (item.get("body") or {}).get("storage", {}).get("value", "")
                    ver_num = (item.get("version") or {}).get("number", 1)
                    created_by = (item.get("history") or {}).get("createdBy") or {}
                    by_info = created_by.get("displayName", "Confluence User")

                    clean_content = _html_to_markdown(body_html)
                    if not clean_content:
                        clean_content = f"# {title}\n\n*Empty Confluence page.*"

                    res = await self.ingest_page(
                        title=title,
                        content=clean_content,
                        page_id=pid,
                        version_num=ver_num,
                        author=by_info,
                        space_key=sp,
                    )
                    synced.append(res)

        return synced

    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Discovers Confluence spaces and root pages as DiscoveredAssets."""
        assets: list[DiscoveredAsset] = []
        if not self.base_url or not self.api_token or not self.user_email:
            return assets

        valid_url = self._normalize_base_url(EncryptionService.validate_external_url(self.base_url))
        auth = (self.user_email.strip(), self.api_token.strip())
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Discovery"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                for sp in self.space_keys:
                    assets.append(
                        DiscoveredAsset(
                            asset_id=f"confluence://{sp}",
                            name=f"Space: {sp}",
                            asset_type="space",
                            source_family=SourceFamily.DOCUMENT,
                            metadata={"space_key": sp},
                        )
                    )
                    url = f"{valid_url}/wiki/rest/api/content?spaceKey={sp}&limit=50"
                    resp = await client.get(url, auth=auth, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("results", []):
                            pid = str(item.get("id"))
                            title = item.get("title", f"Page {pid}")
                            assets.append(
                                DiscoveredAsset(
                                    asset_id=f"confluence://{sp}/page/{pid}",
                                    name=title,
                                    asset_type="page",
                                    source_family=SourceFamily.DOCUMENT,
                                    parent_id=f"confluence://{sp}",
                                    metadata={"space_key": sp, "page_id": pid},
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
        """Fetches raw Confluence page HTML/storage trees and metadata."""
        native_assets: list[RawSourceAsset] = []
        if not self.base_url or not self.api_token or not self.user_email:
            return native_assets

        valid_url = self._normalize_base_url(EncryptionService.validate_external_url(self.base_url))
        auth = (self.user_email.strip(), self.api_token.strip())
        headers = {"Accept": "application/json", "User-Agent": "Context-Trust-Layer-Ingestion"}

        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                for sp in self.space_keys:
                    url = f"{valid_url}/wiki/rest/api/content?spaceKey={sp}&expand=body.storage,version,history&limit=50"
                    resp = await client.get(url, auth=auth, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("results", []):
                            pid = str(item.get("id"))
                            asset_id = f"confluence://{sp}/page/{pid}"
                            if selected_asset_ids and asset_id not in selected_asset_ids:
                                continue

                            title = item.get("title", f"Confluence Page {pid}")
                            body_html = (item.get("body") or {}).get("storage", {}).get("value", "")
                            ver_num = str((item.get("version") or {}).get("number", 1))
                            created_by = (item.get("history") or {}).get("createdBy") or {}
                            by_info = created_by.get("displayName", "Confluence User")

                            native_assets.append(
                                RawSourceAsset(
                                    asset_id=asset_id,
                                    source_family=SourceFamily.DOCUMENT,
                                    native_format="confluence_html",
                                    source_version=ver_num,
                                    raw_payload={
                                        "title": title,
                                        "body_storage_html": body_html,
                                        "version": ver_num,
                                        "author": by_info,
                                    },
                                    locator_metadata={
                                        "space_key": sp,
                                        "page_id": pid,
                                        "page_title": title,
                                        "version": ver_num,
                                    },
                                )
                            )
            except Exception:
                pass
        return native_assets

