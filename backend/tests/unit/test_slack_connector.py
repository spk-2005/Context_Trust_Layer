import json
import uuid
import httpx
import pytest
from datetime import datetime, timezone

from unittest.mock import AsyncMock, MagicMock
from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.base import SyncMode
from app.ingestion.connectors.slack_connector import SlackConnector


def create_mock_transport(handler_fn):
    """Helper to create httpx.MockTransport with given handler."""
    return httpx.MockTransport(handler_fn)


@pytest.mark.asyncio
async def test_auth_test_success():
    """Verify test_connection succeeds when auth.test returns ok: true and required scopes."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/auth.test"
        assert request.headers.get("authorization") == "Bearer xoxb-valid-token"
        content = json.dumps({
            "ok": True,
            "user_id": "U12345",
            "user": "TrustBot",
            "team": "Acme Corp",
            "team_id": "T12345",
            "url": "https://acme.slack.com/",
        }).encode("utf-8")
        headers = {"x-oauth-scopes": "channels:read, channels:history, users:read"}
        return httpx.Response(200, content=content, headers=headers)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(bot_token="xoxb-valid-token", http_client=client)
    res = await connector.test_connection()

    assert res["success"] is True
    assert res["status"] == "ok"
    assert res["details"]["bot_user_id"] == "U12345"
    assert res["details"]["missing_required_scopes"] == []
    assert "Acme Corp" in res["message"]


@pytest.mark.asyncio
async def test_auth_test_missing_scope():
    """Verify test_connection fails when mandatory channels:history scope is missing."""
    def handler(request: httpx.Request) -> httpx.Response:
        content = json.dumps({
            "ok": True,
            "user_id": "U12345",
            "user": "TrustBot",
            "team": "Acme Corp",
            "team_id": "T12345",
            "url": "https://acme.slack.com/",
        }).encode("utf-8")
        # Missing channels:history
        headers = {"x-oauth-scopes": "channels:read, users:read"}
        return httpx.Response(200, content=content, headers=headers)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(bot_token="xoxb-valid-token", http_client=client)
    res = await connector.test_connection()

    assert res["success"] is False
    assert res["status"] == "error"
    assert "channels:history" in res["details"]["missing_required_scopes"]
    assert "missing required OAuth scopes" in res["message"]


@pytest.mark.asyncio
async def test_auth_test_invalid_token():
    """Verify test_connection rejects invalid token prefix or Slack invalid_auth response."""
    # 1. Non-xoxb token
    connector = SlackConnector(bot_token="xoxp-user-token")
    res1 = await connector.test_connection()
    assert res1["success"] is False
    assert "xoxb-" in res1["message"]

    # 2. Slack invalid_auth response
    def handler(request: httpx.Request) -> httpx.Response:
        content = json.dumps({"ok": False, "error": "invalid_auth"}).encode("utf-8")
        return httpx.Response(200, content=content)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector2 = SlackConnector(bot_token="xoxb-bad-token", http_client=client)
    res2 = await connector2.test_connection()
    assert res2["success"] is False
    assert "Invalid token" in res2["message"]


@pytest.mark.asyncio
async def test_rate_limit_backoff_429():
    """Verify HTTP 429 Retry-After triggers sleep and retries transparently."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            headers = {"Retry-After": "0.01"}
            return httpx.Response(429, headers=headers, content=b"rate limited")
        return httpx.Response(
            200,
            content=json.dumps({"ok": True, "team": "Acme", "url": "https://acme.slack.com/"}).encode("utf-8"),
            headers={"x-oauth-scopes": "channels:read,channels:history"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(bot_token="xoxb-rate-limit-token", http_client=client)
    res = await connector.test_connection()

    assert res["success"] is True
    assert calls == 2


@pytest.mark.asyncio
async def test_discover_channels():
    """Verify discover_channels paginates conversations and extracts metadata including is_member."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/conversations.list"
        channels = [
            {
                "id": "C01",
                "name": "incident-management",
                "is_private": False,
                "is_member": True,
                "num_members": 42,
                "topic": {"value": "P0 incident triage"},
            },
            {
                "id": "C02",
                "name": "security-approvals",
                "is_private": True,
                "is_member": False,
                "num_members": 5,
                "topic": {"value": "VP approval gate"},
            },
        ]
        return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(bot_token="xoxb-token", http_client=client)
    assets = await connector.discover_assets()

    assert len(assets) == 2
    assert assets[0].name == "#incident-management"
    assert assets[0].metadata["is_member"] is True
    assert assets[1].name == "#security-approvals"
    assert assets[1].metadata["is_private"] is True
    assert assets[1].metadata["is_member"] is False


@pytest.mark.asyncio
async def test_fetch_native_assets_filtering():
    """Verify noise messages are filtered out, threads fetched, and RawSourceAssets emitted."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth.test":
            return httpx.Response(200, content=json.dumps({"ok": True, "url": "https://acme.slack.com/"}).encode("utf-8"))
        elif path == "/api/conversations.list":
            channels = [{"id": "C01", "name": "general", "is_member": True}]
            return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))
        elif path == "/api/conversations.history":
            messages = [
                # Join noise (should be dropped)
                {"ts": "100.0", "subtype": "channel_join", "user": "U1"},
                # Parent message with replies
                {"ts": "200.0", "user": "U1", "text": "Deploy approved?", "reply_count": 1, "thread_ts": "200.0"},
            ]
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": messages}).encode("utf-8"))
        elif path == "/api/conversations.replies":
            replies = [
                {"ts": "200.0", "user": "U1", "text": "Deploy approved?", "thread_ts": "200.0"},
                {"ts": "201.0", "user": "U2", "text": "Yes, approved by secops.", "thread_ts": "200.0"},
            ]
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": replies}).encode("utf-8"))
        elif path == "/api/users.info":
            uid = request.url.params.get("user")
            name = "Alice" if uid == "U1" else "Bob"
            return httpx.Response(200, content=json.dumps({"ok": True, "user": {"id": uid, "profile": {"display_name": name}}}).encode("utf-8"))
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(
        bot_token="xoxb-test",
        channels=["general"],
        include_replies=True,
        http_client=client,
    )
    assets = await connector.fetch_native_assets()

    # channel_join dropped -> 2 messages left: parent (200.0) + reply (201.0)
    assert len(assets) == 2
    assert assets[0].asset_id == "slack://C01/200.0"
    assert assets[0].raw_payload["speaker"] == "Alice"
    assert assets[1].asset_id == "slack://C01/201.0"
    assert assets[1].raw_payload["speaker"] == "Bob"
    assert assets[1].evidence_locator["permalink"] == "https://acme.slack.com/archives/C01/p2010?thread_ts=200.0&cid=C01"


@pytest.mark.asyncio
async def test_channel_not_in_channel_warning():
    """Verify that not_in_channel error skips the channel and adds an actionable warning."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth.test":
            return httpx.Response(200, content=json.dumps({"ok": True, "url": "https://acme.slack.com/"}).encode("utf-8"))
        elif path == "/api/conversations.list":
            channels = [{"id": "C_SECRET", "name": "secret-ops", "is_member": False}]
            return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))
        elif path == "/api/conversations.history":
            return httpx.Response(200, content=json.dumps({"ok": False, "error": "not_in_channel"}).encode("utf-8"))
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(
        bot_token="xoxb-test",
        channels=["secret-ops"],
        http_client=client,
    )
    assets = await connector.fetch_native_assets()

    assert len(assets) == 0
    assert len(connector.warnings) == 1
    assert "Run /invite @bot" in connector.warnings[0]


@pytest.mark.asyncio
async def test_sync_markdown_rendering():
    """Verify sync converts threads into structured Markdown and mention tags to @DisplayName."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth.test":
            return httpx.Response(200, content=json.dumps({"ok": True, "url": "https://acme.slack.com/"}).encode("utf-8"))
        elif path == "/api/conversations.list":
            channels = [{"id": "C01", "name": "incident-management", "is_member": True}]
            return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))
        elif path == "/api/conversations.history":
            messages = [
                {"ts": "500.0", "user": "U1", "text": "Refunds above $500 must be approved by <@U2>.", "reply_count": 1, "thread_ts": "500.0"}
            ]
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": messages}).encode("utf-8"))
        elif path == "/api/conversations.replies":
            replies = [
                {"ts": "500.0", "user": "U1", "text": "Refunds above $500 must be approved by <@U2>.", "thread_ts": "500.0"},
                {"ts": "501.0", "user": "U2", "text": "Confirmed, effective today.", "thread_ts": "500.0"},
            ]
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": replies}).encode("utf-8"))
        elif path == "/api/users.info":
            uid = request.url.params.get("user")
            name = "Alice" if uid == "U1" else "Bob"
            return httpx.Response(200, content=json.dumps({"ok": True, "user": {"id": uid, "profile": {"display_name": name}}}).encode("utf-8"))
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(
        bot_token="xoxb-test",
        channels=["incident-management"],
        http_client=client,
    )
    # When session is None, sync builds the documents without saving to DB
    assets = await connector.fetch_native_assets()
    assert len(assets) == 2
    # Verify mention substitution
    assert "@Bob" in assets[0].raw_payload["text"]


@pytest.mark.asyncio
async def test_incremental_checkpoint():
    """Verify delta fetch sets oldest timestamp to last_synced_at minus 120s buffer."""
    recorded_oldest = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal recorded_oldest
        path = request.url.path
        if path == "/api/auth.test":
            return httpx.Response(200, content=json.dumps({"ok": True, "url": "https://acme.slack.com/"}).encode("utf-8"))
        elif path == "/api/conversations.list":
            channels = [{"id": "C01", "name": "general", "is_member": True}]
            return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))
        elif path == "/api/conversations.history":
            recorded_oldest = float(request.url.params.get("oldest"))
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": []}).encode("utf-8"))
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(
        bot_token="xoxb-test",
        channels=["general"],
        http_client=client,
    )
    now_ts = datetime.now(timezone.utc).timestamp()
    checkpoint_time = now_ts - 7200.0  # 2 hours ago
    checkpoint = {"last_synced_at": checkpoint_time}
    await connector.fetch_native_assets(sync_mode=SyncMode.INCREMENTAL_DELTA, checkpoint=checkpoint)

    # checkpoint_time - 120.0
    expected_oldest = checkpoint_time - 120.0
    assert abs(recorded_oldest - expected_oldest) < 0.01


@pytest.mark.asyncio
async def test_slack_properties_and_source_family():
    """Verify SlackConnector declares SourceFamily.CONVERSATION and SourceIntent.PROPOSALS_DISCUSSIONS."""
    connector = SlackConnector(bot_token="xoxb-test")
    assert connector.source_family == SourceFamily.CONVERSATION
    assert connector.source_intent == SourceIntent.PROPOSALS_DISCUSSIONS
    assert connector.capabilities["supports_schema_discovery"] is True
    assert connector.capabilities["native_identifier_field"] == "message_ts"


@pytest.mark.asyncio
async def test_slack_backward_compatible_fetch_document():
    """Verify fetch_document returns RawDocumentPayload for legacy Layer 1 compatibility."""
    connector = SlackConnector(bot_token="xoxb-test")
    raw = await connector.fetch_document("C01/12345.67")
    assert raw.source_type == "slack"
    assert raw.document_type == "message"
    assert raw.external_id == "C01/12345.67"


@pytest.mark.asyncio
async def test_mention_with_pipe_and_channel_name_normalization():
    """Verify mentions with pipes <@U123|alice> and <#C456|dev> resolve correctly."""
    connector = SlackConnector(bot_token="xoxb-test")
    text = "Hey <@U123|alice>, check out <#C456|dev> and <https://example.com|docs>!"
    rendered = connector._replace_mentions_sync(text)
    assert "@alice" in rendered
    assert "#dev" in rendered
    assert "[docs](https://example.com)" in rendered


@pytest.mark.asyncio
async def test_sync_with_ingestion_service():
    """Verify sync invokes DocumentIngestionService with valid DocumentCreate containing organization_id."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth.test":
            return httpx.Response(200, content=json.dumps({"ok": True, "url": "https://acme.slack.com/"}).encode("utf-8"))
        elif path == "/api/conversations.list":
            channels = [{"id": "C01", "name": "general", "is_member": True}]
            return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))
        elif path == "/api/conversations.history":
            messages = [{"ts": "300.0", "user": "U1", "text": "Critical decision agreed.", "reply_count": 0}]
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": messages}).encode("utf-8"))
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    mock_session = AsyncMock()
    connector = SlackConnector(
        session=mock_session,
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        bot_token="xoxb-test",
        channels=["general"],
        http_client=client,
    )

    mock_doc = MagicMock()
    mock_ver = MagicMock()
    mock_norm = MagicMock()
    connector.ingestion_service = MagicMock()
    connector.ingestion_service.ingest_document_with_dedup = AsyncMock(
        return_value=(mock_doc, mock_ver, mock_norm, True)
    )

    results = await connector.sync()
    assert len(results) == 1
    doc, ver, is_changed = results[0]
    assert doc is mock_doc
    assert ver is mock_ver
    assert is_changed is True

    # Validate that doc_in passed to ingest_document_with_dedup had correct organization_id
    call_args = connector.ingestion_service.ingest_document_with_dedup.call_args[0]
    doc_in = call_args[0]
    assert doc_in.organization_id == uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert doc_in.source_id == uuid.UUID("22222222-2222-2222-2222-222222222222")
    assert "Slack Thread: #general" in doc_in.title


@pytest.mark.asyncio
async def test_sync_with_file_attachment():
    """Verify messages with file uploads (e.g. Word documents) format file attachments and update titles."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth.test":
            return httpx.Response(200, content=json.dumps({"ok": True, "url": "https://acme.slack.com/"}).encode("utf-8"))
        elif path == "/api/conversations.list":
            channels = [{"id": "C_SOCIAL", "name": "social", "is_member": True}]
            return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))
        elif path == "/api/conversations.history":
            messages = [{
                "ts": "500.0",
                "user": "U_USER1",
                "text": "Check out this assignment.",
                "reply_count": 0,
                "files": [
                    {
                        "id": "F12345",
                        "name": "Basics of python questions.docx",
                        "title": "Basics of python questions.docx",
                        "pretty_type": "Word Document",
                        "size": 25600,
                        "permalink": "https://acme.slack.com/files/U1/F12345/basics.docx",
                    }
                ],
            }]
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": messages}).encode("utf-8"))
        elif path == "/api/users.info":
            return httpx.Response(200, content=json.dumps({
                "ok": True,
                "user": {"id": "U_USER1", "name": "sairam", "profile": {"display_name": "Sairam Pragada"}}
            }).encode("utf-8"))
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        bot_token="xoxb-test",
        channels=["social"],
        http_client=client,
    )

    connector.ingestion_service = MagicMock()
    connector.ingestion_service.ingest_document_with_dedup = AsyncMock(
        return_value=(MagicMock(), MagicMock(), MagicMock(), True)
    )

    results = await connector.sync()
    assert len(results) == 1

    call_args = connector.ingestion_service.ingest_document_with_dedup.call_args[0]
    doc_in = call_args[0]
    assert "Basics of python questions.docx" in doc_in.title
    assert "Basics of python questions.docx" in doc_in.content
    assert "Word Document" in doc_in.content
    assert "https://acme.slack.com/files/U1/F12345/basics.docx" in doc_in.content
    assert "Basics of python questions.docx" in doc_in.metadata["files"]


@pytest.mark.asyncio
async def test_sync_downloads_and_ingests_document_content():
    """Verify that when a file download succeeds, its text is parsed and ingested as both embedded thread content and a standalone document."""
    file_bytes = b"def prime_numbers(n):\n    return [x for x in range(2, n)]"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth.test":
            return httpx.Response(200, content=json.dumps({"ok": True, "url": "https://acme.slack.com/"}).encode("utf-8"))
        elif path == "/api/conversations.list":
            channels = [{"id": "C_SOCIAL", "name": "social", "is_member": True}]
            return httpx.Response(200, content=json.dumps({"ok": True, "channels": channels}).encode("utf-8"))
        elif path == "/api/conversations.history":
            messages = [{
                "ts": "600.0",
                "user": "U_USER1",
                "text": "Here is the python assignment solution.",
                "reply_count": 0,
                "files": [
                    {
                        "id": "F99999",
                        "name": "solution.py",
                        "title": "solution.py",
                        "pretty_type": "Python",
                        "size": len(file_bytes),
                        "url_private_download": "https://files.slack.com/files-pri/T1/download/solution.py",
                        "permalink": "https://acme.slack.com/files/U1/F99999/solution.py",
                    }
                ],
            }]
            return httpx.Response(200, content=json.dumps({"ok": True, "messages": messages}).encode("utf-8"))
        elif path == "/files-pri/T1/download/solution.py":
            return httpx.Response(200, content=file_bytes, headers={"content-type": "text/plain"})
        elif path == "/api/users.info":
            return httpx.Response(200, content=json.dumps({
                "ok": True,
                "user": {"id": "U_USER1", "name": "sairam", "profile": {"display_name": "Sairam Pragada"}}
            }).encode("utf-8"))
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = SlackConnector(
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        bot_token="xoxb-test",
        channels=["social"],
        http_client=client,
    )

    connector.ingestion_service = MagicMock()
    connector.ingestion_service.ingest_document_with_dedup = AsyncMock(
        return_value=(MagicMock(), MagicMock(), MagicMock(), True)
    )

    results = await connector.sync()
    # 2 documents should be ingested: 1 for Slack Thread, 1 for the attached file!
    assert len(results) == 2

    # Check the call arguments to ingest_document_with_dedup
    calls = connector.ingestion_service.ingest_document_with_dedup.call_args_list
    thread_doc = calls[0][0][0]
    file_doc = calls[1][0][0]

    assert "Slack Thread: #social [solution.py]" in thread_doc.title
    assert "prime_numbers" in thread_doc.content
    assert "Extracted Document Content (`solution.py`)" in thread_doc.content

    assert file_doc.title == "Solution"
    assert file_doc.document_type == "document"
    assert "prime_numbers" in file_doc.content
    assert file_doc.external_id == "slack://C_SOCIAL/file/F99999"



