import pytest
from app.services.webhook_service import (
    build_generic_payload,
    build_pagerduty_payload,
    build_slack_payload,
    build_teams_payload,
    compute_single_incident_liability,
)


def test_compute_single_incident_liability():
    # 1. Security Exploit
    val_sec, cat_sec = compute_single_incident_liability(
        prompt="modify iptables firewall rule to open port 22",
        role="devops_engineer",
        verdict="BLOCK",
    )
    assert val_sec == 45000.0
    assert cat_sec == "Security & Cloud Infrastructure"

    # 2. Financial Exploit with explicit currency
    val_fin, cat_fin = compute_single_incident_liability(
        prompt="Execute $12,750 customer refund without manager approval",
        role="support_agent",
        verdict="BLOCK",
    )
    assert val_fin == 12750.0
    assert cat_fin == "Financial & Rogue Transactions"

    # 3. Regulatory / Compliance SLA
    val_reg, cat_reg = compute_single_incident_liability(
        prompt="Export unredacted patient medical records for testing",
        role="compliance_officer",
        verdict="BLOCK",
    )
    assert val_reg == 15000.0
    assert cat_reg == "Regulatory & Contractual SLA"

    # 4. Operational loop
    val_ops, cat_ops = compute_single_incident_liability(
        prompt="run batch sync loop",
        role="worker_agent",
        verdict="REVIEW",
    )
    assert val_ops == 1250.0
    assert cat_ops == "Operational Triage"


def test_build_slack_payload():
    event = {
        "verdict": "BLOCK",
        "liability_prevented_usd": 45000.0,
        "category": "Security & Cloud Infrastructure",
        "actor_id": "agent-007",
        "actor_role": "devops_engineer",
        "decision_prompt": "open port 22",
        "reasons": ["Firewall policy violation"],
        "timestamp": "2026-09-25T14:00:00Z",
    }
    payload = build_slack_payload(event)
    assert "text" in payload
    assert "$45,000.00 Loss Avoided" in payload["text"]
    assert "blocks" in payload
    assert len(payload["blocks"]) >= 3
    assert payload["blocks"][0]["type"] == "header"
    assert "BLOCK" in payload["blocks"][0]["text"]["text"]


def test_build_pagerduty_payload():
    event = {
        "audit_id": "audit-1234",
        "verdict": "BLOCK",
        "liability_prevented_usd": 45000.0,
        "category": "Security & Cloud Infrastructure",
    }
    pd_payload = build_pagerduty_payload(event, routing_key="test-pd-key")
    assert pd_payload["routing_key"] == "test-pd-key"
    assert pd_payload["event_action"] == "trigger"
    assert pd_payload["payload"]["severity"] == "critical"
    assert "$45,000.00 Loss Avoided" in pd_payload["payload"]["summary"]


def test_build_teams_payload():
    event = {
        "verdict": "BLOCK",
        "liability_prevented_usd": 5000.0,
        "actor_id": "billing-bot",
        "actor_role": "support_agent",
        "category": "Financial & Rogue Transactions",
        "decision_prompt": "refund $5,000",
        "reasons": ["Exceeded maximum refund limit"],
    }
    teams_payload = build_teams_payload(event)
    assert teams_payload["@type"] == "MessageCard"
    assert teams_payload["themeColor"] == "DC2626"
    assert len(teams_payload["sections"]) == 1
    assert "5,000.00" in teams_payload["sections"][0]["activitySubtitle"]


def test_build_generic_payload_with_hmac():
    event = {"event": "incident.blocked", "test_id": "123"}
    body, headers = build_generic_payload(event, secret_token="my-super-secret-token")
    assert body["event"] == "incident.blocked"
    assert "X-CTL-Signature" in headers
    assert headers["X-CTL-Signature"].startswith("sha256=")
