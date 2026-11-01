import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceFamily, SourceIntent
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.base import DiscoveredAsset, RawDocumentPayload, RawSourceAsset, SyncMode
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate

logger = logging.getLogger(__name__)


class SlackApiError(Exception):
    """Raised when the Slack API returns an explicit error or non-200 response."""

    def __init__(self, method: str, error: str, status_code: int = 200, details: dict[str, Any] | None = None):
        super().__init__(f"Slack API error during {method}: {error} (HTTP {status_code})")
        self.method = method
        self.error = error
        self.status_code = status_code
        self.details = details or {}


class SlackConnector(BaseConnector):
    """
    Production Layer 2 connector for Slack workspaces, channels, and conversation threads.
    Implements rate-limit backoff (HTTP 429 Retry-After), channel fault tolerance,
    and thread reply tree reconstruction.
    """

    BASE_URL = "https://slack.com/api"

    def __init__(
        self,
        session: AsyncSession = None,
        organization_id: uuid.UUID | None = None,
        source_id: uuid.UUID | None = None,
        bot_token: str | None = None,
        channels: list[str] | str | None = None,
        include_replies: bool = True,
        lookback_days: int = 30,
        connection_config: dict[str, Any] | None = None,
        owner_id: uuid.UUID | None = None,
        http_client: httpx.AsyncClient | None = None,
        source_intent: SourceIntent | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            session=session,
            organization_id=organization_id,
            source_id=source_id,
            connection_config=connection_config,
            owner_id=owner_id,
            source_intent=source_intent or SourceIntent.PROPOSALS_DISCUSSIONS,
            **kwargs,
        )
        cfg = connection_config or {}

        # Token resolution: connection_config -> explicit arg -> env
        raw_token = (
            cfg.get("bot_token")
            or cfg.get("token")
            or cfg.get("access_token")
            or bot_token
            or kwargs.get("token")
            or os.getenv("SLACK_BOT_TOKEN", "")
        )
        self.bot_token = (raw_token or "").strip()

        # Channels resolution
        raw_channels = cfg.get("channels") or channels or []
        if isinstance(raw_channels, str):
            self.channels = [c.strip().lstrip("#") for c in raw_channels.split(",") if c.strip()]
        elif isinstance(raw_channels, (list, tuple, set)):
            self.channels = [str(c).strip().lstrip("#") for c in raw_channels if str(c).strip()]
        else:
            self.channels = []

        self.include_replies = bool(cfg.get("include_replies", include_replies))
        self.lookback_days = max(1, min(365, int(cfg.get("lookback_days", lookback_days))))
        self.include_bot_messages = bool(cfg.get("include_bot_messages", False))

        self._injected_client = http_client
        self._bot_name: str = ""
        self.warnings: list[str] = []
        self._user_cache: dict[str, str] = {}
        self._channel_cache: list[dict[str, Any]] = []
        self.ingestion_service = DocumentIngestionService(session) if session else None

    @property
    def source_family(self) -> SourceFamily:
        return SourceFamily.CONVERSATION

    @property
    def source_intent(self) -> SourceIntent:
        return self._source_intent or SourceIntent.PROPOSALS_DISCUSSIONS

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
            "pagination_type": "cursor",
            "native_identifier_field": "message_ts",
        }

    def _get_client(self) -> httpx.AsyncClient:
        """Returns the injected client or initializes a default client."""
        if self._injected_client is not None:
            return self._injected_client
        return httpx.AsyncClient(timeout=30.0)

    async def _call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Tuple[dict[str, Any], httpx.Headers]:
        """
        Executes an HTTP request to Slack Web API with retry logic:
        - HTTP 429: Respects Retry-After up to 60s, retries up to 5 times.
        - HTTP 5xx: Exponential backoff (1s, 2s, 4s... up to 30s), retries up to 5 times.
        - Checks ok: true in Slack JSON responses.
        """
        url = f"{self.BASE_URL}/{method}"
        req_headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "User-Agent": "Context-Trust-Layer/1.0",
        }
        if headers:
            req_headers.update(headers)

        client = self._get_client()
        should_close = self._injected_client is None

        max_retries = 5
        attempt = 0

        try:
            while True:
                attempt += 1
                try:
                    if json_data is not None:
                        resp = await client.post(url, json=json_data, params=params, headers=req_headers)
                    else:
                        resp = await client.get(url, params=params, headers=req_headers)

                    # Handle 429 Rate Limiting
                    if resp.status_code == 429:
                        if attempt >= max_retries:
                            raise SlackApiError(method, "ratelimited_max_retries_exceeded", 429)
                        retry_after = float(resp.headers.get("Retry-After", "1"))
                        sleep_seconds = min(retry_after, 60.0)
                        logger.warning("Slack API 429 for %s. Sleeping %s seconds (attempt %s/%s).", method, sleep_seconds, attempt, max_retries)
                        await asyncio.sleep(sleep_seconds)
                        continue

                    # Handle 5xx Server Errors
                    if 500 <= resp.status_code < 600:
                        if attempt >= max_retries:
                            raise SlackApiError(method, f"http_server_error_{resp.status_code}", resp.status_code)
                        backoff = min(2 ** (attempt - 1), 30.0)
                        logger.warning("Slack API %s HTTP %s. Backoff %s seconds (attempt %s/%s).", method, resp.status_code, backoff, attempt, max_retries)
                        await asyncio.sleep(backoff)
                        continue

                    # Try parsing JSON
                    try:
                        data = resp.json()
                    except Exception:
                        raise SlackApiError(method, "invalid_json_response", resp.status_code)

                    if not data.get("ok", False):
                        err_code = data.get("error", "unknown_error")
                        raise SlackApiError(method, err_code, resp.status_code, details=data)

                    return data, resp.headers

                except httpx.RequestError as exc:
                    if attempt >= max_retries:
                        raise SlackApiError(method, f"network_error: {str(exc)}", 0)
                    backoff = min(2 ** (attempt - 1), 30.0)
                    logger.warning("Network error calling Slack %s: %s. Retrying in %ss.", method, exc, backoff)
                    await asyncio.sleep(backoff)

        finally:
            if should_close:
                await client.aclose()

    async def _paginate(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        item_key: str = "channels",
    ) -> list[dict[str, Any]]:
        """Paginates through Slack endpoints using cursor-based pagination."""
        all_items: list[dict[str, Any]] = []
        p = dict(params or {})
        cursor = None

        while True:
            if cursor:
                p["cursor"] = cursor

            data, _ = await self._call(method, params=p)
            items = data.get(item_key, [])
            if isinstance(items, list):
                all_items.extend(items)

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return all_items

    async def download_file_bytes(self, file_url: str) -> Optional[bytes]:
        """
        Downloads a private file from Slack using the Bot token.
        Follows redirects and validates that the response is binary content, not an HTML error.
        """
        if not file_url or not self.bot_token:
            return None
        client = self._get_client()
        should_close = self._injected_client is None
        try:
            req_headers = {"Authorization": f"Bearer {self.bot_token}"}
            resp = await client.get(file_url, headers=req_headers, follow_redirects=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "").lower()
                # If Slack returned HTML login or error page instead of binary file
                if "text/html" in content_type or resp.content[:200].strip().startswith(b"<!DOCTYPE html"):
                    logger.warning("Slack file download returned HTML instead of document bytes. Token likely lacks 'files:read' scope.")
                    return None
                return resp.content
            elif resp.status_code == 403:
                logger.warning("Slack file download returned HTTP 403 Forbidden. Bot token lacks 'files:read' scope: %s", file_url)
                return None
            else:
                logger.warning("Failed to download Slack file from %s: HTTP %s", file_url, resp.status_code)
                return None
        except Exception as exc:
            logger.warning("Exception downloading Slack file %s: %s", file_url, exc)
            return None
        finally:
            if should_close:
                await client.aclose()

    async def test_connection(self) -> dict[str, Any]:
        """
        Verifies authentication against auth.test and checks required OAuth scopes.
        Matches Jira and Confluence return structure.
        """
        if not self.bot_token:
            return {
                "success": False,
                "status": "error",
                "message": "Slack Bot User OAuth Token is required.",
                "details": {"error": "not_authed"},
            }

        if not self.bot_token.startswith("xoxb-"):
            return {
                "success": False,
                "status": "error",
                "message": "Invalid Slack token format. Must be a Bot User OAuth Token starting with 'xoxb-'.",
                "details": {"error": "invalid_token_type"},
            }

        try:
            data, headers = await self._call("auth.test")
            raw_scopes = headers.get("x-oauth-scopes", "")
            granted_scopes = [s.strip() for s in raw_scopes.split(",") if s.strip()]

            required_scopes = {"channels:read", "channels:history"}
            missing_required = [s for s in required_scopes if s not in granted_scopes]

            recommended_scopes = {"files:read", "users:read"}
            missing_recommended = [s for s in recommended_scopes if s not in granted_scopes]

            bot_user_id = data.get("user_id", "")
            bot_name = data.get("user", "")
            self._bot_name = bot_name
            team = data.get("team", "")
            team_id = data.get("team_id", "")
            workspace_url = data.get("url", "")

            if missing_required:
                return {
                    "success": False,
                    "status": "error",
                    "message": f"Slack bot token is missing required OAuth scopes: {', '.join(missing_required)}.",
                    "details": {
                        "bot_user_id": bot_user_id,
                        "team": team,
                        "team_id": team_id,
                        "workspace_url": workspace_url,
                        "granted_scopes": granted_scopes,
                        "missing_required_scopes": missing_required,
                        "missing_recommended_scopes": missing_recommended,
                    },
                }

            success_msg = f"Connected to Slack workspace '{team}' as @{bot_name} ({bot_user_id})."
            if "files:read" in missing_recommended:
                success_msg += " (Tip: add 'files:read' scope to ingest contents of uploaded documents like Word/PDF)."

            return {
                "success": True,
                "status": "ok",
                "message": success_msg,
                "details": {
                    "bot_user_id": bot_user_id,
                    "bot_name": bot_name,
                    "team": team,
                    "team_id": team_id,
                    "workspace_url": workspace_url,
                    "granted_scopes": granted_scopes,
                    "missing_required_scopes": [],
                    "missing_recommended_scopes": missing_recommended,
                },
            }

        except SlackApiError as e:
            msg_map = {
                "invalid_auth": "Slack authentication failed: Invalid token.",
                "token_expired": "Slack token has expired.",
                "token_revoked": "Slack token has been revoked.",
                "account_inactive": "Slack account is inactive.",
            }
            clean_msg = msg_map.get(e.error, f"Slack connection test failed: {e.error}")
            return {
                "success": False,
                "status": "error",
                "message": clean_msg,
                "details": {"error": e.error, "status_code": e.status_code},
            }
        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "message": f"Slack connection test failed: {str(exc)}",
                "details": {"error": str(exc)},
            }

    @classmethod
    async def discover_channels(cls, bot_token: str) -> list[dict[str, Any]]:
        """
        Classmethod discovery function backing the /api/v1/sources/discover endpoint.
        """
        connector = cls(bot_token=bot_token)
        assets = await connector.discover_assets()
        return [
            {
                "id": a.metadata.get("channel_id") or a.asset_id.replace("slack://", ""),
                "name": a.metadata.get("name") or a.name.lstrip("#"),
                "channel_name": a.metadata.get("name") or a.name.lstrip("#"),
                "display_name": a.name if a.name.startswith("#") else f"#{a.name}",
                "type": a.asset_type,
                "is_private": a.metadata.get("is_private", False),
                "is_member": a.metadata.get("is_member", False),
                "num_members": a.metadata.get("num_members", 0),
                "topic": a.metadata.get("topic", ""),
            }
            for a in assets
        ]

    async def discover_assets(self) -> List[DiscoveredAsset]:
        """
        Discovers public and private Slack channels accessible to the bot.
        """
        if not self.bot_token:
            return []

        try:
            # First try both public and private
            channels_raw = await self._paginate(
                "conversations.list",
                params={"types": "public_channel,private_channel", "exclude_archived": "true", "limit": 200},
                item_key="channels",
            )
        except SlackApiError as e:
            if "missing_scope" in e.error:
                # Fallback to public channels only if groups:read is missing
                logger.warning("Missing groups:read scope for Slack private channels. Falling back to public channels.")
                self.warnings.append("Missing 'groups:read' scope; only public channels discovered.")
                channels_raw = await self._paginate(
                    "conversations.list",
                    params={"types": "public_channel", "exclude_archived": "true", "limit": 200},
                    item_key="channels",
                )
            else:
                raise e

        self._channel_cache = channels_raw
        discovered: list[DiscoveredAsset] = []

        for ch in channels_raw:
            ch_id = ch["id"]
            name = ch.get("name", ch_id)
            is_priv = ch.get("is_private", False)
            topic = ch.get("topic", {}).get("value", "")
            num_members = ch.get("num_members", 0)
            is_member = ch.get("is_member", False)

            discovered.append(
                DiscoveredAsset(
                    asset_id=f"slack://{ch_id}",
                    name=f"#{name}",
                    asset_type="channel",
                    source_family=SourceFamily.CONVERSATION,
                    metadata={
                        "channel_id": ch_id,
                        "name": name,
                        "channel_name": name,
                        "is_private": is_priv,
                        "topic": topic,
                        "num_members": num_members,
                        "is_member": is_member,
                    },
                )
            )

        return discovered

    async def _resolve_channel_id(self, channel_target: str) -> Optional[dict[str, Any]]:
        """Resolves channel ID or clean name to channel metadata."""
        clean_target = channel_target.strip().lstrip("#").lower()
        if not self._channel_cache:
            try:
                await self.discover_assets()
            except Exception as e:
                logger.warning("Failed to populate channel cache: %s", e)

        for ch in self._channel_cache:
            if (
                ch.get("id", "").lower() == clean_target
                or ch.get("name", "").lower() == clean_target
                or ch.get("name_normalized", "").lower() == clean_target
            ):
                return ch
        return None

    async def _resolve_username(self, user_id: str) -> str:
        """Resolves user ID to display name with local caching."""
        if not user_id:
            return "Unknown User"
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        try:
            data, _ = await self._call("users.info", params={"user": user_id})
            user_data = data.get("user", {})
            profile = user_data.get("profile", {})
            name = (
                profile.get("display_name")
                or profile.get("real_name")
                or user_data.get("real_name")
                or user_data.get("name")
                or user_id
            )
            self._user_cache[user_id] = name
            return name
        except Exception:
            self._user_cache[user_id] = user_id
            return user_id

    def _replace_mentions_sync(self, text: str) -> str:
        """Synchronously replaces cached user tags and channel links."""
        # Replace user mentions <@U12345|username> or <@U12345>
        def user_sub(m):
            uid = m.group(1)
            display = self._user_cache.get(uid) or m.group(2) or uid
            return f"@{display}"

        text = re.sub(r"<@([A-Za-z0-9_]+)(?:\|([^>]+))?>", user_sub, text)

        # Replace channel mentions <#C12345|general> or <#C12345>
        def chan_sub(m):
            return f"#{m.group(2) if m.group(2) else m.group(1)}"

        text = re.sub(r"<#([A-Za-z0-9_]+)(?:\|([^>]+))?>", chan_sub, text)

        # Replace URLs <http...|label> or <http...>
        def url_sub(m):
            url = m.group(1)
            label = m.group(2)
            return f"[{label}]({url})" if label else url

        text = re.sub(r"<(https?://[^|>]+)(?:\|([^>]+))?>", url_sub, text)
        return text

    async def fetch_native_assets(
        self,
        selected_asset_ids: Optional[List[str]] = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: Optional[dict[str, Any]] = None,
    ) -> List[RawSourceAsset]:
        """
        Layer 2: Fetches native Slack conversation messages and reply threads.
        Emits one RawSourceAsset per message (slack://{channel_id}/{message_ts}).
        """
        if not self.bot_token:
            return []

        # Determine target channels
        target_channel_identifiers = []
        if selected_asset_ids:
            for aid in selected_asset_ids:
                clean_id = aid.replace("slack://", "").split("/")[0]
                target_channel_identifiers.append(clean_id)
        elif self.channels:
            target_channel_identifiers = list(self.channels)
        else:
            # Discover all available channels if none specified
            disc = await self.discover_assets()
            target_channel_identifiers = [a.metadata["channel_id"] for a in disc]

        # Calculate oldest timestamp cutoff
        now_dt = datetime.now(timezone.utc)
        lookback_floor = (now_dt - timedelta(days=self.lookback_days)).timestamp()

        oldest_ts = lookback_floor
        if sync_mode == SyncMode.INCREMENTAL_DELTA and checkpoint:
            last_synced_at = checkpoint.get("last_synced_at")
            if last_synced_at:
                try:
                    if isinstance(last_synced_at, str):
                        dt = datetime.fromisoformat(last_synced_at.replace("Z", "+00:00"))
                    elif isinstance(last_synced_at, (int, float)):
                        dt = datetime.fromtimestamp(last_synced_at, timezone.utc)
                    else:
                        dt = now_dt
                    oldest_ts = max(lookback_floor, dt.timestamp() - 120.0)
                except Exception as exc:
                    logger.warning("Could not parse sync_checkpoint timestamp: %s", exc)

        workspace_url = ""
        try:
            auth_info, _ = await self._call("auth.test")
            workspace_url = auth_info.get("url", "")
            if not self._bot_name:
                self._bot_name = auth_info.get("user", "")
            if workspace_url and not workspace_url.endswith("/"):
                workspace_url += "/"
        except Exception:
            pass

        raw_assets: list[RawSourceAsset] = []

        for ch_target in target_channel_identifiers:
            ch_meta = await self._resolve_channel_id(ch_target)
            ch_id = ch_meta["id"] if ch_meta else ch_target.lstrip("#")
            ch_name = ch_meta.get("name", ch_id) if ch_meta else ch_id

            try:
                # Fetch channel message history
                history_messages = await self._paginate(
                    "conversations.history",
                    params={"channel": ch_id, "oldest": str(oldest_ts), "limit": 200},
                    item_key="messages",
                )
            except SlackApiError as e:
                if e.error == "not_in_channel":
                    # Attempt to automatically join public channel if bot has permissions
                    joined = False
                    try:
                        join_res, _ = await self._call("conversations.join", json_data={"channel": ch_id})
                        if join_res.get("ok"):
                            joined = True
                            logger.info("Automatically joined public Slack channel #%s (%s)", ch_name, ch_id)
                            history_messages = await self._paginate(
                                "conversations.history",
                                params={"channel": ch_id, "oldest": str(oldest_ts), "limit": 200},
                                item_key="messages",
                            )
                    except Exception as join_exc:
                        logger.debug("Automatic join of channel #%s failed: %s", ch_name, join_exc)
                        joined = False

                    if not joined:
                        bot_display = f"@{self._bot_name}" if self._bot_name else "@bot"
                        warn_msg = (
                            f"Skipping #{ch_name} ({ch_id}): bot is not a member of #{ch_name}. "
                            f"In Slack, please open #{ch_name} and Run /invite {bot_display} to enable ingestion."
                        )
                        logger.warning(warn_msg)
                        self.warnings.append(warn_msg)
                        continue
                elif e.error in ("channel_not_found", "is_archived", "missing_scope"):
                    warn_msg = f"Skipping #{ch_name} ({ch_id}): {e.error}."
                    logger.warning(warn_msg)
                    self.warnings.append(warn_msg)
                    continue
                else:
                    raise e

            # Collect messages and associated thread replies
            all_channel_messages: list[dict[str, Any]] = []

            for msg in history_messages:
                # Filter out system noise
                subtype = msg.get("subtype", "")
                if subtype in ("channel_join", "channel_leave", "pin_added", "channel_topic", "channel_purpose"):
                    continue
                if not self.include_bot_messages and msg.get("bot_id"):
                    continue

                all_channel_messages.append(msg)

                # Fetch full thread replies if this is a parent message with replies
                reply_count = msg.get("reply_count", 0)
                thread_ts = msg.get("thread_ts") or msg.get("ts")
                if self.include_replies and reply_count > 0:
                    try:
                        replies = await self._paginate(
                            "conversations.replies",
                            params={"channel": ch_id, "ts": thread_ts, "limit": 200},
                            item_key="messages",
                        )
                        # The first message in replies is the parent message; add subsequent replies
                        for rep in replies[1:]:
                            if not self.include_bot_messages and rep.get("bot_id"):
                                continue
                            all_channel_messages.append(rep)
                    except SlackApiError as r_err:
                        logger.warning("Failed to fetch replies for thread %s in %s: %s", thread_ts, ch_id, r_err)

            # Prefetch usernames for any mentioned users
            user_ids_to_resolve = set()
            for m in all_channel_messages:
                if m.get("user"):
                    user_ids_to_resolve.add(m["user"])
                for match in re.findall(r"<@([A-Z0-9]+)>", m.get("text", "")):
                    user_ids_to_resolve.add(match)

            for uid in user_ids_to_resolve:
                await self._resolve_username(uid)

            # Convert each message into an individual RawSourceAsset
            for m in all_channel_messages:
                msg_ts = m.get("ts", "")
                if not msg_ts:
                    continue

                thread_id = m.get("thread_ts") or msg_ts
                user_id = m.get("user", "")
                speaker_name = self._user_cache.get(user_id, user_id or "Unknown User")
                raw_text = m.get("text", "")
                rendered_text = self._replace_mentions_sync(raw_text)

                # Process attached files (e.g. documents, PDFs, docx, spreadsheets)
                files_list = m.get("files", [])
                file_lines = []
                extracted_files = []

                for f in files_list:
                    fname = f.get("name") or f.get("title") or "Attachment"
                    ftype = f.get("pretty_type") or f.get("filetype", "").upper() or "Document"
                    download_url = f.get("url_private_download") or f.get("url_private") or ""
                    furl = f.get("permalink") or download_url
                    fsize = f.get("size")
                    size_str = f" ({round(fsize / 1024, 1)} KB)" if fsize else ""

                    # Attempt to download and extract full text from the file
                    file_text = ""
                    if download_url:
                        raw_bytes = await self.download_file_bytes(download_url)
                        if raw_bytes:
                            try:
                                from app.ingestion.universal_file_parser import UniversalFileParser
                                doc_title = fname.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
                                file_text = UniversalFileParser.parse_file(
                                    filename=fname,
                                    raw_bytes=raw_bytes,
                                    doc_title=doc_title,
                                )
                            except Exception as parse_err:
                                logger.warning("Failed to parse Slack file %s: %s", fname, parse_err)
                        else:
                            warn = f"Slack file '{fname}' could not be downloaded: please add 'files:read' OAuth scope to your Slack Bot token to ingest attached document contents."
                            if warn not in self.warnings:
                                self.warnings.append(warn)

                    if file_text:
                        doc_head = f"📎 **Attached Document**: [{fname}]({furl})" if furl else f"📎 **Attached Document**: `{fname}`"
                        file_lines.append(f"{doc_head} - *{ftype}*{size_str}\n\n#### Extracted Document Content (`{fname}`):\n\n{file_text.strip()}\n")
                        extracted_files.append({
                            "file_id": f.get("id"),
                            "name": fname,
                            "title": fname.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title(),
                            "content": file_text.strip(),
                            "size": fsize,
                            "permalink": furl,
                            "filetype": ftype,
                        })
                    else:
                        if furl:
                            file_lines.append(f"📎 **Uploaded File**: [{fname}]({furl}) - *{ftype}*{size_str}")
                        else:
                            file_lines.append(f"📎 **Uploaded File**: `{fname}` - *{ftype}*{size_str}")

                if file_lines:
                    file_block = "\n".join(file_lines)
                    rendered_text = f"{rendered_text}\n\n{file_block}" if rendered_text else file_block

                edited_ts = m.get("edited", {}).get("ts") if isinstance(m.get("edited"), dict) else None
                version_str = str(edited_ts or msg_ts)

                # Synthesize permalink without burning extra API calls
                clean_ts = msg_ts.replace(".", "")
                permalink = f"{workspace_url}archives/{ch_id}/p{clean_ts}"
                if thread_id != msg_ts:
                    permalink += f"?thread_ts={thread_id}&cid={ch_id}"

                try:
                    iso_time = datetime.fromtimestamp(float(msg_ts), timezone.utc).isoformat()
                except Exception:
                    iso_time = str(msg_ts)

                payload_data = dict(m)
                payload_data.update({
                    "speaker": speaker_name,
                    "author": speaker_name,
                    "user_name": speaker_name,
                    "timestamp": iso_time,
                    "id": msg_ts,
                    "message_id": msg_ts,
                    "parent_id": m.get("thread_ts") if m.get("thread_ts") != msg_ts else None,
                    "channel": f"#{ch_name}",
                    "channel_name": ch_name,
                    "channel_id": ch_id,
                    "thread_id": thread_id,
                    "text": rendered_text,
                    "content": rendered_text,
                    "body": rendered_text,
                    "permalink": permalink,
                    "files": files_list,
                    "file_names": [f.get("name") for f in files_list if f.get("name")],
                    "extracted_files": extracted_files,
                })

                locator_meta = {
                    "channel_id": ch_id,
                    "channel_name": ch_name,
                    "channel": f"#{ch_name}",
                    "message_ts": msg_ts,
                    "thread_ts": thread_id,
                    "thread_id": thread_id,
                    "permalink": permalink,
                }

                raw_assets.append(
                    RawSourceAsset(
                        asset_id=f"slack://{ch_id}/{msg_ts}",
                        source_id=self.source_id,
                        native_format="slack_message",
                        source_family=SourceFamily.CONVERSATION,
                        source_version=version_str,
                        raw_payload=payload_data,
                        locator_metadata=locator_meta,
                        evidence_locator=locator_meta,
                        metadata={
                            "channel_id": ch_id,
                            "channel_name": ch_name,
                            "user_id": user_id,
                            "speaker": speaker_name,
                            "author": speaker_name,
                            "thread_id": thread_id,
                            "permalink": permalink,
                        },
                    )
                )

        return raw_assets

    async def fetch_document(self, external_id: str) -> RawDocumentPayload:
        """Backward compatibility with Layer 1 connector stub contract."""
        return RawDocumentPayload(
            organization_id=self.organization_id,
            source_id=self.source_id,
            title=f"Slack Message {external_id}",
            content="",
            source_type="slack",
            external_id=external_id,
            document_type="message",
        )

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion, bool]]:
        """
        Sync records from external source into documents and document_versions (legacy bridge).
        Renders complete Markdown threads and calls DocumentIngestionService.ingest_document_with_dedup.
        """
        if not self.bot_token:
            raise RuntimeError("Slack sync failed: Bot token is not configured.")

        # 1. Fetch native messages
        checkpoint = (self.connection_config or {}).get("sync_checkpoint")
        native_assets = await self.fetch_native_assets(sync_mode=SyncMode.INITIAL_FULL, checkpoint=checkpoint)

        # Group messages by thread (external_id = slack://{ch_id}/{thread_id})
        threads: dict[str, list[dict[str, Any]]] = {}
        thread_metadata: dict[str, dict[str, Any]] = {}

        for asset in native_assets:
            p = asset.raw_payload
            ch_id = p.get("channel_id", "")
            th_id = p.get("thread_id", p.get("id"))
            ext_id = f"slack://{ch_id}/{th_id}"

            if ext_id not in threads:
                threads[ext_id] = []
                thread_metadata[ext_id] = {
                    "channel": p.get("channel", ""),
                    "channel_id": ch_id,
                    "thread_ts": th_id,
                    "permalink": p.get("permalink", ""),
                }
            threads[ext_id].append(p)

        results: list[tuple[Document, DocumentVersion, bool]] = []
        ingestion_service = self.ingestion_service or (DocumentIngestionService(self.session) if self.session else None)

        for ext_id, msgs in threads.items():
            meta = thread_metadata[ext_id]
            # Sort messages chronologically by float timestamp
            msgs.sort(key=lambda x: float(x.get("id", "0") or 0))

            ch_name = meta["channel"]
            th_ts = meta["thread_ts"]
            permalink = meta["permalink"]
            msg_count = len(msgs)

            root_msg = msgs[0]
            root_speaker = root_msg.get("speaker", "Unknown User")
            root_time = root_msg.get("timestamp", "")
            root_text = root_msg.get("text", "")

            # Build readable Markdown document
            lines = [
                f"# Slack Thread: {ch_name}",
                f"**Channel**: `{ch_name}` (`{meta['channel_id']}`) | **Thread TS**: `{th_ts}` | **Messages**: {msg_count}",
                f"**Permalink**: {permalink}",
                "",
                "---",
                "",
                f"### Message by {root_speaker} at {root_time}",
                "",
                root_text,
                "",
            ]

            for reply in msgs[1:]:
                spk = reply.get("speaker", "Unknown User")
                tm = reply.get("timestamp", "")
                txt = reply.get("text", "")
                lines.extend([
                    f"### Reply by {spk} at {tm}",
                    "",
                    txt,
                    "",
                ])

            full_markdown = "\n".join(lines).strip()
            participants = list({m.get("speaker", "") for m in msgs if m.get("speaker")})
            latest_ts = msgs[-1].get("id", th_ts)

            # Collect any file names uploaded in this thread
            all_file_names = []
            for m in msgs:
                all_file_names.extend([f.get("name") for f in m.get("files", []) if f.get("name")])

            file_suffix = f" [{all_file_names[0]}]" if all_file_names else ""
            title_text = f"Slack Thread: {ch_name}{file_suffix} ({th_ts})"

            doc_create = DocumentCreate(
                organization_id=self.organization_id,
                source_id=self.source_id,
                owner_id=self.owner_id,
                title=title_text,
                document_type="slack_message",
                content=full_markdown,
                external_id=ext_id,
                metadata={
                    "connector": "slack",
                    "channel": ch_name,
                    "channel_id": meta["channel_id"],
                    "thread_ts": th_ts,
                    "message_count": msg_count,
                    "participants": participants,
                    "latest_ts": latest_ts,
                    "permalink": permalink,
                    "files": all_file_names,
                },
            )

            if ingestion_service is not None:
                doc, version, _, is_changed = await ingestion_service.ingest_document_with_dedup(doc_create)
                results.append((doc, version, is_changed))

                # Ingest attached documents as dedicated, first-class documents as well
                for m in msgs:
                    for fdoc in m.get("extracted_files", []):
                        f_id = fdoc.get("file_id") or uuid.uuid4().hex[:8]
                        f_title = fdoc.get("title") or fdoc.get("name")
                        file_doc_create = DocumentCreate(
                            organization_id=self.organization_id,
                            source_id=self.source_id,
                            owner_id=self.owner_id,
                            title=f"{f_title}",
                            document_type="document",
                            content=fdoc.get("content", ""),
                            external_id=f"slack://{meta['channel_id']}/file/{f_id}",
                            metadata={
                                "connector": "slack",
                                "channel": ch_name,
                                "channel_id": meta["channel_id"],
                                "filename": fdoc.get("name"),
                                "file_id": f_id,
                                "filetype": fdoc.get("filetype", ""),
                                "permalink": fdoc.get("permalink", ""),
                                "thread_ts": th_ts,
                            },
                        )
                        if fdoc.get("content"):
                            f_doc, f_ver, _, f_changed = await ingestion_service.ingest_document_with_dedup(file_doc_create)
                            results.append((f_doc, f_ver, f_changed))

        return results
