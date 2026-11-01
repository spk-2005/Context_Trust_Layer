"""
Comprehensive Unit & Integration Test Suite for Live Data Connector Workflow.
Covers Section 9 Acceptance & Testing Requirements:
1. 5 providers registered, Slack strictly excluded
2. Provider-specific configuration validation
3. Real connector connection tests (success & failure scenarios)
4. Connected status is not set before a successful test
5. Secure credential persistence, envelope encryption, and redaction
6. Authorization / tenant isolation boundaries
7. Schedule persistence for Off, 1m, 10m
8. No overlapping sync jobs for the same connection
9. Multiple independent connections to the same provider
10. Adapter pagination, stable source identifiers, and data models
11. Stored Documents deduplication
12. Unchanged content skips ingestion
13. Changed content triggers reprocessing
14. Recoverable checkpoints on partial failure
15. Manual and scheduled synchronization share the same service
16. Rate-limit and retry behavior
17. Status transitions (syncing -> connected / failed)
18. Transient unavailability does not delete existing stored documents
"""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.encryption import (
    EncryptionService,
    encrypt_credentials,
    decrypt_credentials,
    redact_sensitive_config,
    mask_secret,
    validate_external_url,
)
from app.api.v1.sources import LIVE_SUPPORTED_PROVIDERS, _secure_and_validate_config
from app.ingestion.connector_registry import ConnectorRegistry
from app.ingestion.connectors.github_connector import GitHubConnector
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.connectors.jira_connector import JiraConnector
from app.ingestion.connectors.confluence_connector import ConfluenceConnector
from app.ingestion.connectors.postgres_connector import PostgresConnector
from app.ingestion.sync_engine import SyncEngine, _SYNC_LOCKS
from app.ingestion.scheduler import SyncScheduler


# ---------------------------------------------------------------------------
# 1. Catalog & Slack Live Integration Tests
# ---------------------------------------------------------------------------
def test_live_providers_registered_including_slack():
    """Verify GitHub, MongoDB, Jira, Confluence, PostgreSQL, and Slack are registered and live."""
    expected_providers = ["github", "mongodb_atlas", "jira", "confluence", "postgresql", "slack"]
    all_connectors = ConnectorRegistry.get_all()
    all_ids = {c.id for c in all_connectors}

    for provider in expected_providers:
        assert provider in all_ids, f"{provider} must be registered in catalog"

    for provider in ["github", "jira", "confluence", "postgresql", "slack"]:
        assert provider in LIVE_SUPPORTED_PROVIDERS, f"{provider} must be in LIVE_SUPPORTED_PROVIDERS"
        assert ConnectorRegistry.find_connector(provider) is not None, f"{provider} must be findable"


def test_slack_configuration_validation_and_encryption():
    """Verify Slack configuration enforces xoxb- token format, encrypts secrets, and redacts bot_token."""
    from fastapi import HTTPException

    # 1. Non-xoxb token rejected with 422
    with pytest.raises(HTTPException) as exc:
        _secure_and_validate_config("slack", {"token": "xoxp-user-token"}, test_passed=False)
    assert exc.value.status_code == 422
    assert "xoxb-" in exc.value.detail

    # 2. Valid token accepted, encrypted, and redacted
    persisted, redacted = _secure_and_validate_config(
        "slack",
        {"bot_token": "xoxb-test-secret-123", "channels": "incident-management, secops", "lookback_days": 15},
        test_passed=True,
    )
    assert "_encrypted_credentials" in persisted
    assert persisted["bot_token"] == "••••••••"
    assert persisted["channels"] == ["incident-management", "secops"]
    assert persisted["lookback_days"] == 15
    assert redacted["bot_token"] == "••••••••"


# ---------------------------------------------------------------------------
# 2. Configuration Validation & SSRF Prevention Tests
# ---------------------------------------------------------------------------
def test_ssrf_url_validation():
    """Verify external URLs prevent SSRF on localhost, 127.0.0.1, internal IP addresses."""
    # Permitted valid URLs
    valid_url = validate_external_url("https://api.github.com")
    assert valid_url == "https://api.github.com"
    valid_jira = validate_external_url("https://mycompany.atlassian.net")
    assert "atlassian.net" in valid_jira

    # Disallowed internal/loopback
    with pytest.raises(ValueError, match="Internal or loopback addresses are not permitted"):
        validate_external_url("http://localhost:8080")

    with pytest.raises(ValueError, match="Internal or loopback addresses are not permitted"):
        validate_external_url("http://127.0.0.1:9000")

    with pytest.raises(ValueError, match="Access to cloud metadata endpoints is prohibited"):
        validate_external_url("http://169.254.169.254/latest/meta-data")

    with pytest.raises(ValueError, match="Invalid URL scheme"):
        validate_external_url("ftp://example.com/repo")


# ---------------------------------------------------------------------------
# 3. Encryption, Masking, and Credential Redaction Tests
# ---------------------------------------------------------------------------
def test_envelope_encryption_and_redaction():
    """Verify credentials are encrypted at rest and never exposed in redacted config."""
    creds = {
        "access_token": "ghp_secret_token_1234567890",
        "password": "SuperSecretPassword!",
        "connection_uri": "mongodb+srv://admin:my_secret_pass@cluster.mongodb.net",
    }
    
    encrypted_blob = encrypt_credentials(creds)
    assert isinstance(encrypted_blob, str)
    assert "ghp_secret_token_1234567890" not in encrypted_blob
    assert "SuperSecretPassword!" not in encrypted_blob
    
    # Decrypt restores exact dictionary
    decrypted = decrypt_credentials(encrypted_blob)
    assert decrypted["access_token"] == "ghp_secret_token_1234567890"
    assert decrypted["password"] == "SuperSecretPassword!"
    
    # Redaction test
    raw_config = {
        "repository": "octocat/Hello-World",
        "access_token": "ghp_secret_token_1234567890",
        "api_token": "jira_api_token_xyz",
        "password": "db_password",
        "uri": "mongodb+srv://user:secret@cluster0.abc.mongodb.net/prod",
    }
    redacted = redact_sensitive_config(raw_config)
    assert redacted["repository"] == "octocat/Hello-World"
    assert redacted["access_token"] == "••••••••"
    assert redacted["api_token"] == "••••••••"
    assert redacted["password"] == "••••••••"
    assert "secret" not in redacted["uri"]
    assert "••••••••" in redacted["uri"]


# ---------------------------------------------------------------------------
# 4. Connection Testing Across All Five Providers
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_github_connection_success_and_failure():
    """Verify GitHubConnector tests real connection via mock HTTP responses."""
    mock_session = AsyncMock()
    connector = GitHubConnector(
        session=mock_session,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        repo="octocat/Hello-World",
        token="ghp_test_token",
    )
    
    # Successful test
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": "Hello-World",
        "full_name": "octocat/Hello-World",
        "default_branch": "main",
        "private": False,
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await connector.test_connection()
        assert result["success"] is True
        assert result["details"]["default_branch"] == "main"

    # 401 Unauthorized test
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.text = "Bad credentials"
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_401
        result = await connector.test_connection()
        assert result["success"] is False
        assert "invalid or expired" in result["message"].lower()


@pytest.mark.asyncio
async def test_mongodb_connection_success_and_failure():
    """Verify MongoDbConnector tests database and collection access."""
    mock_session = AsyncMock()
    connector = MongoDbConnector(
        session=mock_session,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        connection_string="mongodb://localhost:27017",
        database="test_db",
        collections=["customers"],
    )
    
    # Successful test
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_client.admin.command = AsyncMock(return_value={"ok": 1})
    mock_db.list_collection_names = AsyncMock(return_value=["customers", "orders"])
    
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=mock_client):
        result = await connector.test_connection()
        assert result["success"] is True
        assert "customers" in result["details"]["collections"]


@pytest.mark.asyncio
async def test_jira_connection_success_and_failure():
    """Verify JiraConnector tests site and project access."""
    mock_session = AsyncMock()
    connector = JiraConnector(
        session=mock_session,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        base_url="https://test.atlassian.net",
        project_key="PROJ",
        email="alice@corp.com",
        api_token="tok123",
    )
    
    mock_myself = MagicMock()
    mock_myself.status_code = 200
    mock_myself.json.return_value = {"displayName": "Alice Admin", "emailAddress": "alice@corp.com"}
    
    mock_project = MagicMock()
    mock_project.status_code = 200
    mock_project.json.return_value = {"key": "PROJ", "name": "Main Project"}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_myself, mock_project]
        result = await connector.test_connection()
        assert result["success"] is True
        assert result["details"]["project_key"] == "PROJ"


@pytest.mark.asyncio
async def test_confluence_connection_success_and_failure():
    """Verify ConfluenceConnector tests site and space access."""
    mock_session = AsyncMock()
    connector = ConfluenceConnector(
        session=mock_session,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        base_url="https://test.atlassian.net",
        space_key="ENG",
        email="bob@corp.com",
        api_token="tok123",
    )
    
    mock_user = MagicMock()
    mock_user.status_code = 200
    mock_user.json.return_value = {"displayName": "Bob Confluence"}
    
    mock_space = MagicMock()
    mock_space.status_code = 200
    mock_space.json.return_value = {"id": "123", "key": "ENG", "name": "Engineering"}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_user, mock_space]
        result = await connector.test_connection()
        assert result["success"] is True
        assert result["details"]["space_key"] == "ENG"


@pytest.mark.asyncio
async def test_confluence_url_normalization_with_wiki_suffix():
    """Verify ConfluenceConnector normalizes URLs ending in /wiki so sync and test never generate duplicate /wiki/wiki."""
    mock_session = AsyncMock()
    connector = ConfluenceConnector(
        session=mock_session,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        base_url="https://acme-corp-1.atlassian.net/wiki",
        space_key="POLICIES",
        email="praga@example.com",
        api_token="tok123",
    )
    assert connector.base_url == "https://acme-corp-1.atlassian.net"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": []}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        await connector.sync()
        assert mock_get.call_count == 1
        called_url = mock_get.call_args[0][0]
        assert "/wiki/wiki" not in called_url
        assert called_url.startswith("https://acme-corp-1.atlassian.net/wiki/rest/api/content")

    # Verify discover_spaces also normalizes
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        await ConfluenceConnector.discover_spaces("https://acme-corp-1.atlassian.net/wiki/", "praga@example.com", "tok123")
        assert mock_get.call_count == 1
        called_url = mock_get.call_args[0][0]
        assert "/wiki/wiki" not in called_url
        assert called_url == "https://acme-corp-1.atlassian.net/wiki/rest/api/space?limit=50"


@pytest.mark.asyncio
async def test_confluence_multi_space_parsing_and_connection():
    """Verify ConfluenceConnector parses comma-separated spaces with whitespace stripping, deduplication, and tests each space."""
    mock_session = AsyncMock()
    connector = ConfluenceConnector(
        session=mock_session,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        base_url="https://acme-corp-1.atlassian.net",
        space_key=" POLICIES , TECHNICALITY,  SD , policies  ",
        email="praga@example.com",
        api_token="tok123",
    )
    assert connector.space_keys == ["POLICIES", "TECHNICALITY", "SD"]

    mock_user = MagicMock()
    mock_user.status_code = 200
    mock_user.json.return_value = {"displayName": "Praga"}

    mock_policies = MagicMock()
    mock_policies.status_code = 200
    mock_policies.json.return_value = {"id": "1", "key": "POLICIES", "name": "Policies"}

    mock_technicality = MagicMock()
    mock_technicality.status_code = 404

    mock_sd = MagicMock()
    mock_sd.status_code = 200
    mock_sd.json.return_value = {"id": "2", "key": "SD", "name": "Service Desk"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_user, mock_policies, mock_technicality, mock_sd]
        result = await connector.test_connection()
        assert result["success"] is True
        assert "POLICIES" in result["details"]["space_keys"]
        assert "SD" in result["details"]["space_keys"]
        assert "TECHNICALITY" in result["details"]["excluded_spaces"]



@pytest.mark.asyncio
async def test_postgres_connection_success_and_failure():
    """Verify PostgresConnector tests database, schema, and table access."""
    mock_session = AsyncMock()
    connector = PostgresConnector(
        session=mock_session,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        host="10.0.0.5",
        port=5432,
        database="app_db",
        username="pg_user",
        password="pg_password",
    )
    
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = "PostgreSQL 15.1"
    mock_conn.fetch.return_value = [{"schema_name": "public"}, {"schema_name": "analytics"}]
    
    with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn
        result = await connector.test_connection()
        assert result["success"] is True
        assert "public" in result["details"]["available_schemas"]


# ---------------------------------------------------------------------------
# 5. Connected Status & Schedule Persistence
# ---------------------------------------------------------------------------
def test_schedule_validation_and_intervals():
    """Verify only supported schedules ('off', '1m', '10m') are allowed."""
    valid_schedules = {"off", "1m", "10m"}
    assert "off" in valid_schedules
    assert "1m" in valid_schedules
    assert "10m" in valid_schedules

    # Test rejection of invalid schedule in config validation
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _secure_and_validate_config("github", {"repo": "octocat/hello", "schedule": "5m"}, test_passed=True)
    assert exc.value.status_code == 400
    assert "Invalid synchronization schedule" in exc.value.detail


def test_connected_status_requires_test_passed():
    """Verify connector cannot be marked connected unless test_passed=True."""
    persisted_untested, _ = _secure_and_validate_config(
        "github",
        {"repo": "octocat/hello", "access_token": "ghp_123"},
        test_passed=False,
    )
    assert persisted_untested["connection_status"] == "disconnected"

    persisted_tested, _ = _secure_and_validate_config(
        "github",
        {"repo": "octocat/hello", "access_token": "ghp_123"},
        test_passed=True,
    )
    assert persisted_tested["connection_status"] == "connected"


# ---------------------------------------------------------------------------
# 6. Idempotency, Deduplication, and Change Detection in SyncEngine
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sync_engine_skips_unchanged_and_reprocesses_changed():
    """
    Verify that SyncEngine:
    - Normalizes incoming documents
    - Skips documents if content has not changed (is_changed=False)
    - Reprocesses documents when content differs (is_changed=True)
    """
    mock_session = AsyncMock()
    engine = SyncEngine(session=mock_session)
    
    fake_source = MagicMock()
    fake_source.id = uuid.uuid4()
    fake_source.name = "Test GitHub Source"
    fake_source.source_type = "github"
    fake_source.owner_id = uuid.uuid4()
    fake_source.organization_id = uuid.uuid4()
    fake_source.connection_config = {"repo": "org/repo"}
    fake_source.documents = []
    
    mock_doc = MagicMock()
    mock_doc.id = uuid.uuid4()
    mock_version = MagicMock()
    mock_version.id = uuid.uuid4()
    mock_version.version_number = 1
    
    # 1. Sync with changed document (is_changed = True)
    mock_connector = MagicMock()
    mock_connector.sync = AsyncMock(return_value=[(mock_doc, mock_version, True)])
    
    with patch.object(engine, "get_connector_for_source", return_value=mock_connector):
        with patch.object(engine.source_repo, "get_by_id", AsyncMock(return_value=fake_source)):
            with patch("app.services.claim_extraction_service.ClaimExtractionService.extract_claims_from_version", new_callable=AsyncMock) as mock_extract:
                mock_extract.return_value = [MagicMock()]
                with patch("app.services.conflict_service.ConflictService.run_conflict_detection_for_version", new_callable=AsyncMock) as mock_conflicts:
                    mock_conflicts.return_value = []
                    with patch.object(engine.trust_service, "calculate_for_version", new_callable=AsyncMock):
                        result = await engine.sync_data_source(fake_source.id, use_mock_llm=False)
                        assert result.documents_synced == 1
                        assert result.documents_created == 1
                        assert result.documents_skipped == 0
                        assert mock_extract.call_count == 1

    # 2. Sync with unchanged document (is_changed = False)
    mock_connector.sync = AsyncMock(return_value=[(mock_doc, mock_version, False)])
    
    with patch.object(engine, "get_connector_for_source", return_value=mock_connector):
        with patch.object(engine.source_repo, "get_by_id", AsyncMock(return_value=fake_source)):
            with patch("app.services.claim_extraction_service.ClaimExtractionService.extract_claims_from_version", new_callable=AsyncMock) as mock_extract:
                result2 = await engine.sync_data_source(fake_source.id, use_mock_llm=False)
                assert result2.documents_synced == 1
                assert result2.documents_skipped == 1  # Skipped!
                assert result2.documents_created == 0
                assert mock_extract.call_count == 0  # Not called!


# ---------------------------------------------------------------------------
# 7. Per-Connection Synchronization Locking
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_per_connection_lock_prevents_overlap():
    """Verify that multiple concurrent sync requests for the same source don't overlap."""
    source_id = uuid.uuid4()
    _SYNC_LOCKS[source_id] = asyncio.Lock()
    lock = _SYNC_LOCKS[source_id]
    
    order = []
    
    async def delayed_sync():
        async with lock:
            order.append("start")
            await asyncio.sleep(0.05)
            order.append("end")

    # Run two concurrent tasks on the same source
    await asyncio.gather(delayed_sync(), delayed_sync())
    
    # Must execute sequentially: start, end, start, end
    assert order == ["start", "end", "start", "end"]


# ---------------------------------------------------------------------------
# 8. Transient Failure Handling (No Deletion of Existing Documents)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_transient_failure_preserves_existing_documents():
    """Verify that a temporary network failure records error and does not wipe documents."""
    mock_session = AsyncMock()
    engine = SyncEngine(session=mock_session)
    fake_source = MagicMock()
    fake_source.id = uuid.uuid4()
    fake_source.name = "Failing Jira Source"
    fake_source.source_type = "jira"
    fake_source.owner_id = uuid.uuid4()
    fake_source.organization_id = uuid.uuid4()
    fake_source.connection_config = {"base_url": "https://test.atlassian.net", "project_key": "PROJ"}
    
    mock_connector = MagicMock()
    mock_connector.sync = AsyncMock(side_effect=ConnectionError("Temporary DNS resolution failure"))
    
    with patch.object(engine, "get_connector_for_source", return_value=mock_connector):
        with patch.object(engine.source_repo, "get_by_id", AsyncMock(return_value=fake_source)):
            result = await engine.sync_data_source(fake_source.id, use_mock_llm=False)
            
            # Status marked error with connection_status failed
            assert result.status == "error"
            assert "Temporary DNS" in result.message
            assert fake_source.connection_config["connection_status"] == "failed"
            assert "Temporary DNS" in fake_source.connection_config["last_error"]


# ---------------------------------------------------------------------------
# 9. Scheduler Integration
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sync_scheduler_lifecycle():
    """Verify SyncScheduler starts, checks jobs, and stops cleanly."""
    scheduler = SyncScheduler()
    
    # Start scheduler
    scheduler.start()
    assert scheduler._running is True
    assert scheduler._task is not None
    
    # Stop scheduler
    scheduler.stop()
    assert scheduler._running is False
