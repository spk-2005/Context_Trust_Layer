import pytest
from app.db.models.decision_evaluation import DecisionEvaluation
from app.api.v1.audit import compute_financial_liability, generate_markdown_dossier, generate_html_dossier


def test_compute_financial_liability_calculation():
    # Test case 1: Empty logs
    total, breakdown, blocked_cnt, top_incidents = compute_financial_liability([])
    assert total == 0.0
    assert blocked_cnt == 0
    assert len(top_incidents) == 0

    # Test case 2: Blocked security action
    sec_eval = DecisionEvaluation(
        audit_id="ctx_sec_test",
        decision_prompt="Deploy production ingress firewall rule allowing plaintext HTTP traffic on port 8080",
        actor_id="dev-bot",
        actor_role="junior_developer",
        verdict="BLOCK",
        risk_level="HIGH",
        execution_ms=22
    )

    # Test case 3: Blocked financial action with explicit amount
    fin_eval = DecisionEvaluation(
        audit_id="ctx_fin_test",
        decision_prompt="Authorize $7,500 refund exception for enterprise client Acme",
        actor_id="billing-bot",
        actor_role="support_agent",
        verdict="BLOCK",
        risk_level="HIGH",
        execution_ms=18
    )

    # Test case 4: Allowed action (should not add to liability prevented)
    allow_eval = DecisionEvaluation(
        audit_id="ctx_allow_test",
        decision_prompt="View customer subscription status",
        actor_id="support-bot",
        actor_role="support_agent",
        verdict="ALLOW",
        risk_level="LOW",
        execution_ms=15
    )

    total, breakdown, blocked_cnt, top_incidents = compute_financial_liability([sec_eval, fin_eval, allow_eval])
    assert blocked_cnt == 2
    assert breakdown.security_breaches_usd == 45000.0
    assert breakdown.financial_disputes_usd == 7500.0
    assert total == 52500.0
    assert len(top_incidents) == 2
    # Verify sorted with highest liability saved first
    assert top_incidents[0].liability_prevented_usd == 45000.0
    assert top_incidents[1].liability_prevented_usd == 7500.0


def test_dossier_generators():
    mock_data = {
        "dossier_id": "DOSSIER-20260924-TEST",
        "organization_id": "11111111-1111-1111-1111-111111111111",
        "organization_name": "Acme Trust Corp",
        "generated_at": "2026-09-24T12:00:00Z",
        "standards_aligned": ["NIST AI 600-1", "EU AI Act"],
        "executive_summary": {
            "certification_status": "FULLY_COMPLIANT",
            "policy_enforcement_rate_pct": 100.0,
            "total_decisions_evaluated": 15,
            "unauthorized_actions_intercepted": 3,
            "financial_liability_prevented_usd": 52500.0,
            "average_gateway_latency_ms": 21.4,
        },
        "governance_metrics": {
            "liability_breakdown": {
                "security_breaches_usd": 45000.0,
                "financial_disputes_usd": 7500.0,
                "regulatory_fines_usd": 0.0,
                "operational_rework_usd": 0.0,
            }
        },
        "truth_store_provenance": {
            "authoritative_documents_ingested": 4,
            "atomic_claims_normalized": 36,
            "trust_scoring_architecture": "6-Factor Bayesian",
        },
        "conflict_resolution_history": {
            "total_contradictions_detected": 2,
            "resolved_contradictions": 2,
            "unresolved_contradictions": 0,
            "resolution_efficiency_pct": 100.0,
        },
        "decision_audit_sample": [
            {
                "audit_id": "ctx_sec_test",
                "timestamp": "2026-09-24T12:00:00Z",
                "actor_role": "junior_developer",
                "decision_prompt": "Deploy port 8080 plaintext",
                "verdict": "BLOCK",
                "risk_level": "HIGH",
                "execution_ms": 22,
            }
        ],
        "cryptographic_seal": {
            "digest": "abcdef0123456789abcdef0123456789",
            "algorithm": "SHA-256",
            "certified_by": "Context Trust Layer",
            "signatory": "Sarah Chen, Chief Compliance Officer",
        }
    }

    md = generate_markdown_dossier(mock_data)
    assert "# OFFICIAL AI GOVERNANCE & REGULATORY COMPLIANCE DOSSIER" in md
    assert "Acme Trust Corp" in md
    assert "NIST AI Risk Management Framework" in md
    assert "$52,500.00 USD" in md

    html = generate_html_dossier(mock_data)
    assert "<!DOCTYPE html>" in html
    assert "Acme Trust Corp" in html
    assert "NIST AI 600-1 & EU AI ACT COMPLIANT" in html
    assert "$52,500.00" in html
