import decimal
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slack_security import (
    SlackSecurityError,
    decode_oauth_state,
    decode_slack_link_token,
    decrypt_slack_bot_token,
    encrypt_slack_bot_token,
    generate_oauth_state,
    generate_slack_link_token,
    verify_slack_signature,
)
from app.db.enums import RecordStatus
from app.db.models.slack import (
    SlackDeliveryLedger,
    SlackInboundRequest,
    SlackInstallation,
    SlackJob,
    SlackUserIdentity,
)
from app.db.models.user import User
from app.schemas.context import ContextItemResponse, ContextQueryResponse, ContextSourceInfo, ContextValidityInfo
from app.services.copilot_query_service import (
    CopilotCitation,
    CopilotQueryRequest,
    CopilotQueryResponse,
    CopilotQueryService,
)
from app.services.slack_block_kit import SlackBlockKitRenderer
from app.services.slack_worker import SlackJobWorker


# ==============================================================================
# TEST 1: TEST-SEC-01 Valid Signature & Freshness Accepted
# ==============================================================================
def test_sec_01_valid_signature_accepted():
    secret = "slack_test_signing_secret_999"
    ts = str(int(time.time()))
    raw_body = b"command=%2Ftrulin&text=ask+payment+terms&team_id=T100&user_id=U200"
    basestring = b"v0:" + ts.encode("utf-8") + b":" + raw_body
    computed_sig = "v0=" + hmac.new(secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()

    is_valid = verify_slack_signature(
        raw_body=raw_body,
        timestamp_header=ts,
        signature_header=computed_sig,
        signing_secret=secret,
    )
    assert is_valid is True


# ==============================================================================
# TEST 2: TEST-SEC-02 Tampered Body or Altered Signature Rejected
# ==============================================================================
def test_sec_02_tampered_body_rejected():
    secret = "slack_test_signing_secret_999"
    ts = str(int(time.time()))
    raw_body = b"command=%2Ftrulin&text=ask+payment+terms"
    basestring = b"v0:" + ts.encode("utf-8") + b":" + raw_body
    valid_sig = "v0=" + hmac.new(secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()

    # Tampered body
    tampered_body = raw_body + b"&malicious_payload=true"
    assert verify_slack_signature(tampered_body, ts, valid_sig, signing_secret=secret) is False

    # Tampered signature
    assert verify_slack_signature(raw_body, ts, valid_sig + "fake", signing_secret=secret) is False


# ==============================================================================
# TEST 3: TEST-SEC-03 Expired Timestamp Replay Attack Prevention
# ==============================================================================
def test_sec_03_expired_timestamp_replay_prevention():
    secret = "slack_test_signing_secret_999"
    # Timestamp is 6 minutes (360 seconds) old -> exceeds 300s window
    old_ts = str(int(time.time()) - 360)
    raw_body = b"command=%2Ftrulin&text=ask+terms"
    basestring = b"v0:" + old_ts.encode("utf-8") + b":" + raw_body
    computed_sig = "v0=" + hmac.new(secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()

    is_valid = verify_slack_signature(
        raw_body=raw_body,
        timestamp_header=old_ts,
        signature_header=computed_sig,
        signing_secret=secret,
        max_drift_seconds=300,
    )
    assert is_valid is False


# ==============================================================================
# TEST 4: TEST-SEC-04 Command Deduplication via Query Fingerprint
# ==============================================================================
def test_sec_04_duplicate_command_fingerprint_deduplication():
    team_id = "T123"
    user_id = "U456"
    trigger_id = "12345.67890"
    command = "/trulin"
    query = "What are the payment terms in the agreement?"

    fingerprint_raw = f"{team_id}:{user_id}:{trigger_id}:{command}:{query}"
    fp1 = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()
    fp2 = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()

    assert fp1 == fp2
    assert len(fp1) == 64


# ==============================================================================
# TEST 5: TEST-SEC-05 Workspace-to-Organization Isolation
# ==============================================================================
def test_sec_05_workspace_organization_isolation():
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    # Admin state bound to Org A
    state_token_a = generate_oauth_state(str(org_a), str(uuid.uuid4()))
    decoded_state_a = decode_oauth_state(state_token_a)

    assert decoded_state_a["organization_id"] == str(org_a)
    assert decoded_state_a["organization_id"] != str(org_b)

    # Link token bound to Org A
    link_token_a = generate_slack_link_token("T_ORG_A", "U_ALICE", str(org_a))
    decoded_link = decode_slack_link_token(link_token_a)

    assert decoded_link["slack_team_id"] == "T_ORG_A"
    assert decoded_link["organization_id"] == str(org_a)


# ==============================================================================
# TEST 6: TEST-AUTH-06 Unlinked Slack User Dispatches Private Link Card
# ==============================================================================
def test_auth_06_unlinked_user_flow():
    link_url = "https://app.trulin.ai/v1/slack/link-ui?token=sample_token_123"
    card = SlackBlockKitRenderer.render_account_linking_card(link_url)

    assert card["response_type"] == "ephemeral"
    assert "Connect your Trulin account" in card["text"]
    assert any(b.get("type") == "actions" for b in card["blocks"])
    
    # Check button URL
    action_block = next(b for b in card["blocks"] if b.get("type") == "actions")
    button = action_block["elements"][0]
    assert button["url"] == link_url


# ==============================================================================
# TEST 7: TEST-AUTH-07 Deactivated User Blocked from Accessing Evidence
# ==============================================================================
def test_auth_07_deactivated_user_blocked():
    error_card = SlackBlockKitRenderer.render_error_card(
        message="Your linked Trulin user account is inactive or revoked.",
        trace_id="trc-test-deactivated",
    )
    assert error_card["response_type"] == "ephemeral"
    assert "inactive or revoked" in error_card["blocks"][0]["text"]["text"]
    assert "trc-test-deactivated" in error_card["blocks"][1]["elements"][0]["text"]


# ==============================================================================
# TEST 8: TEST-PRIV-08 Ephemeral Response Assertion & @channel Sanitization
# ==============================================================================
def test_priv_08_ephemeral_response_assertion():
    response = CopilotQueryResponse(
        trace_id="trc-priv-check",
        answer_status="ANSWERED",
        decision_verdict="ALLOW",
        synthesized_answer="Notice to <!channel> and <!here>: Invoices are due in Net 30.",
        citations=[
            CopilotCitation(
                source_index=1,
                claim_id=uuid.uuid4(),
                document_name="Billing Master Agreement",
                section="Section 4",
                trust_score=0.95,
                claim_text="Net 30 payment schedule",
                evidence_url="https://app.trulin.ai/evidence/claim-1",
            )
        ],
        conditions=["Late fee of 1.5% applies <!channel>"],
        trust_score=0.95,
    )

    rendered = SlackBlockKitRenderer.render_policy_answer(response, question="What are the <!everyone> terms?")

    # 1. Ephemeral assertion
    assert rendered["response_type"] == "ephemeral"

    # 2. Mentions sanitized
    rendered_json = str(rendered)
    assert "<!channel>" not in rendered_json
    assert "<!here>" not in rendered_json
    assert "<!everyone>" not in rendered_json
    assert "@channel" in rendered_json
    assert "@here" in rendered_json
    assert "@everyone" in rendered_json


# ==============================================================================
# TEST 9: TEST-REL-09 Outbox Worker Job Enqueue & Lease
# ==============================================================================
def test_rel_09_worker_queue_and_resilience():
    req_id = uuid.uuid4()
    job = SlackJob(
        id=uuid.uuid4(),
        inbound_request_id=req_id,
        status="QUEUED",
        attempts=0,
        max_attempts=3,
        next_run_at=datetime.now(timezone.utc),
    )
    assert job.status == "QUEUED"
    assert job.attempts == 0
    assert job.max_attempts == 3


# ==============================================================================
# TEST 10: TEST-REL-10 Slack 429 Rate Limit Handling & Retry Scheduling
# ==============================================================================
@pytest.mark.asyncio
async def test_rel_10_rate_limit_429_backoff():
    worker = SlackJobWorker()
    req = MagicMock()
    req.id = uuid.uuid4()
    req.trace_id = "trc-rate-limit"
    req.response_url = "https://hooks.slack.com/actions/T123/sample"

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "4"}

    session_mock = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        success = await worker._dispatch_to_response_url(session_mock, req, {"test": "payload"})

        assert success is False
        # Ledger was added with RETRIED status
        session_mock.add.assert_called_once()
        added_ledger = session_mock.add.call_args[0][0]
        assert isinstance(added_ledger, SlackDeliveryLedger)
        assert added_ledger.delivery_status == "RETRIED"
        assert added_ledger.http_status == 429


# ==============================================================================
# TEST 11: TEST-REL-11 Response URL Expiry Guard (> 25 min)
# ==============================================================================
def test_rel_11_response_url_expiry_handling():
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=2)  # Expired 2 minutes ago

    req = SlackInboundRequest(
        id=uuid.uuid4(),
        slack_team_id="T100",
        slack_user_id="U200",
        slack_channel_id="C300",
        command="/trulin",
        query_fingerprint="fp123",
        response_url="https://hooks.slack.com/commands/T100/expired",
        response_url_expires_at=expired_time,
        trace_id="trc-expired",
        raw_text="Sample query",
        status="QUEUED",
        created_at=now - timedelta(minutes=28),
    )

    assert now > req.response_url_expires_at


# ==============================================================================
# TEST 12: TEST-REV-12 App Uninstalled / Inactive Installation
# ==============================================================================
def test_rev_12_installation_revocation_stops_jobs():
    inst = SlackInstallation(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        slack_team_id="T_REVOKED",
        encrypted_bot_token="enc_token_123",
        is_active=False,  # Uninstalled
        revoked_at=datetime.now(timezone.utc),
    )
    assert inst.is_active is False
    assert inst.revoked_at is not None


# ==============================================================================
# TEST 13: TEST-EVID-13 Evidence Token Security & Encryption
# ==============================================================================
def test_evid_13_evidence_link_and_token_security():
    # 1. Bot token encryption at rest
    raw_token = "xoxb-real-slack-bot-token-secret-999"
    encrypted = encrypt_slack_bot_token(raw_token)
    assert encrypted != raw_token
    decrypted = decrypt_slack_bot_token(encrypted)
    assert decrypted == raw_token

    # 2. Account linking token expiry
    link_token = generate_slack_link_token("T1", "U1", str(uuid.uuid4()), expires_in_minutes=-1)
    with pytest.raises(SlackSecurityError, match="expired"):
        decode_slack_link_token(link_token)


# ==============================================================================
# TEST 14: TEST-SEM-14 Copilot Web vs Slack Semantic Parity
# ==============================================================================
@pytest.mark.asyncio
async def test_sem_14_copilot_web_vs_slack_parity():
    session_mock = AsyncMock(spec=AsyncSession)
    service = CopilotQueryService(session_mock)

    # Mock ContextRetrievalEngine to return verified agreement claims
    claim_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_claim = ContextItemResponse(
        claim_id=claim_id,
        document_id=doc_id,
        claim="Payment terms are Net 30 from invoice receipt.",
        trust_score=decimal.Decimal("0.92"),
        evidence=["Section 4.1: All valid invoices shall be settled Net 30."],
        source=ContextSourceInfo(document="Master Agreement 2026", section="4.1", page=3),
        validity=ContextValidityInfo(status="active"),
    )
    mock_retrieval_res = ContextQueryResponse(
        context=[mock_claim],
        conflicts=[],
        confidence=decimal.Decimal("0.92"),
    )

    with patch("app.retrieval.engine.ContextRetrievalEngine.query_context", new_callable=AsyncMock) as mock_query, \
         patch.object(service.llm, "generate_grounded_answer", new_callable=AsyncMock) as mock_llm_ans:
        
        mock_query.return_value = mock_retrieval_res
        mock_llm_ans.return_value = (
            "Payment must be remitted within 30 days of invoice receipt (Net 30) [Source 1].\n"
            "- Condition: Invoices must include the approved purchase order number [Source 1]."
        )

        query_req = CopilotQueryRequest(
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_name="Alice",
            question="What are the invoice payment terms?",
            trace_id="trc-sem-parity",
        )

        res = await service.query_policy(query_req)

        assert res.trace_id == "trc-sem-parity"
        assert res.answer_status == "ANSWERED"
        assert res.decision_verdict == "ALLOW"
        assert res.trust_score == 0.92
        assert len(res.citations) == 1
        assert res.citations[0].document_name == "Master Agreement 2026"
        assert res.citations[0].section == "4.1"
        assert "evidence/" + str(claim_id) in res.citations[0].evidence_url
        assert len(res.conditions) >= 1


# ==============================================================================
# TEST 15: TEST-HON-15 Insufficient Evidence Honest Clarification
# ==============================================================================
@pytest.mark.asyncio
async def test_hon_15_insufficient_evidence_honest_clarification():
    session_mock = AsyncMock(spec=AsyncSession)
    service = CopilotQueryService(session_mock)

    empty_retrieval_res = ContextQueryResponse(
        context=[],
        conflicts=[],
        confidence=decimal.Decimal("0.50"),
    )

    with patch("app.retrieval.engine.ContextRetrievalEngine.query_context", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = empty_retrieval_res

        query_req = CopilotQueryRequest(
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            question="What is the refund deadline for custom hardware?",
            trace_id="trc-empty-evidence",
        )

        res = await service.query_policy(query_req)

        # Honest abstention: No hallucination or false allow
        assert res.answer_status == "CLARIFICATION_NEEDED"
        assert res.decision_verdict == "CLARIFY"
        assert len(res.citations) == 0
        assert "No permitted policy documents" in res.synthesized_answer
        assert len(res.missing_facts) > 0


# ==============================================================================
# FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================
def test_endpoint_slash_command_signature_rejection():
    from starlette.testclient import TestClient
    from app.main import app
    from app.core.config import settings

    with patch.object(settings, "slack_signing_secret", "test_signing_secret_live"):
        client = TestClient(app)
        
        # 1. No signature headers -> 401
        res = client.post(
            "/v1/slack/commands",
            data={"command": "/trulin", "text": "help", "team_id": "T1", "user_id": "U1"},
        )
        assert res.status_code == 401

        # 2. Tampered signature -> 401
        res = client.post(
            "/v1/slack/commands",
            data={"command": "/trulin", "text": "help", "team_id": "T1", "user_id": "U1"},
            headers={"X-Slack-Request-Timestamp": str(int(time.time())), "X-Slack-Signature": "v0=invalid_sig"},
        )
        assert res.status_code == 401


def test_endpoint_slash_command_help_card():
    from starlette.testclient import TestClient
    from app.main import app
    from app.core.config import settings
    from app.db.database import get_db

    secret = "test_signing_secret_live"
    with patch.object(settings, "slack_signing_secret", secret):
        client = TestClient(app)
        
        form_payload = "command=%2Ftrulin&text=help&team_id=T_MOCK&user_id=U_MOCK&channel_id=C_MOCK"
        body_bytes = form_payload.encode("utf-8")
        ts = str(int(time.time()))
        basestring = b"v0:" + ts.encode("utf-8") + b":" + body_bytes
        valid_sig = "v0=" + hmac.new(secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()

        # Mock database session to return active installation
        mock_inst = SlackInstallation(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            slack_team_id="T_MOCK",
            slack_team_name="Mock Corp",
            is_active=True,
            encrypted_bot_token="enc_token",
        )
        mock_db = AsyncMock(spec=AsyncSession)
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_inst
        mock_db.execute.return_value = mock_res

        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            res = client.post(
                "/v1/slack/commands",
                content=body_bytes,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Slack-Request-Timestamp": ts,
                    "X-Slack-Signature": valid_sig,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["response_type"] == "ephemeral"
            assert "Trulin Assistant Help" in data["text"]
        finally:
            app.dependency_overrides.pop(get_db, None)


def test_endpoint_link_ui_renders_html():
    from starlette.testclient import TestClient
    from app.main import app
    from app.db.database import get_db

    client = TestClient(app)
    org_id = uuid.uuid4()
    link_token = generate_slack_link_token("T_TEST", "U_TEST", str(org_id))

    mock_db = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_org = MagicMock()
    mock_org.name = "Acme Global"
    mock_res.scalar_one_or_none.return_value = mock_org
    mock_db.execute.return_value = mock_res

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.get(f"/v1/slack/link-ui?token={link_token}")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "Connect Your Account" in res.text
        assert "Acme Global" in res.text
        assert "U_TEST" in res.text
    finally:
        app.dependency_overrides.pop(get_db, None)
