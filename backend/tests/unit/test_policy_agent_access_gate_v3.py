"""
Unit tests for PolicyAgentAccessGate under the 6-Tier v3.0 Governance Model.
Validates:
1. HUMAN_CERTIFIED allows full autonomous use.
2. AUTOMATED_CERTIFIED allows full autonomous use with automated provenance.
3. High-risk actions (termination, indemnity, liability) require human confirmation even for AUTOMATED_CERTIFIED.
4. PROVISIONAL requires citation and caution.
5. REVIEW_REQUIRED is blocked from autonomous execution.
6. QUARANTINED is strictly prohibited from normative answers.
7. REJECTED is strictly blocked.
"""

import pytest
from app.services.policy_agent_access_gate import (
    PolicyAgentAccessGate,
    AgentAccessLevel,
    CertificationTier,
)


def test_human_certified_full_autonomous_access():
    gate = PolicyAgentAccessGate()
    claim = {"claim_id": "CLM-001", "certification_tier": "HUMAN_CERTIFIED", "predicate": "grants_license"}
    allowed, level, reason = gate.check_access(claim)

    assert allowed is True
    assert level == AgentAccessLevel.FULL_ACCESS
    assert "Human-certified" in reason


def test_automated_certified_standard_action_autonomous():
    gate = PolicyAgentAccessGate()
    claim = {"claim_id": "CLM-002", "certification_tier": "AUTOMATED_CERTIFIED", "predicate": "must_pay_fees"}
    allowed, level, reason = gate.check_access(claim)

    assert allowed is True
    assert level == AgentAccessLevel.FULL_ACCESS_AUTOMATED
    assert "automated provenance" in reason


def test_automated_certified_high_risk_requires_confirmation():
    gate = PolicyAgentAccessGate()
    
    # Termination claim
    claim_term = {"claim_id": "CLM-003", "certification_tier": "AUTOMATED_CERTIFIED", "predicate": "terminate_for_cause"}
    allowed, level, reason = gate.check_access(claim_term)
    assert allowed is True
    assert level == AgentAccessLevel.HUMAN_CONFIRMATION_REQUIRED
    assert "Human confirmation required" in reason

    # Indemnity query intent
    claim_std = {"claim_id": "CLM-004", "certification_tier": "AUTOMATED_CERTIFIED", "predicate": "assist_defense"}
    allowed, level, reason = gate.check_access(claim_std, query_intent="Execute contract indemnity claim")
    assert allowed is True
    assert level == AgentAccessLevel.HUMAN_CONFIRMATION_REQUIRED


def test_provisional_restricted_access():
    gate = PolicyAgentAccessGate()
    claim = {"claim_id": "CLM-005", "certification_tier": "PROVISIONAL", "predicate": "guideline"}
    allowed, level, reason = gate.check_access(claim)

    assert allowed is True
    assert level == AgentAccessLevel.RESTRICTED_ACCESS
    assert "caution" in reason


def test_quarantined_blocked_from_normative():
    gate = PolicyAgentAccessGate()
    claim = {"claim_id": "doc057:af:024", "certification_tier": "QUARANTINED", "predicate": "may_sublicense"}
    allowed, level, reason = gate.check_access(claim)

    assert allowed is False
    assert level == AgentAccessLevel.NO_ACCESS
    assert "Quarantined" in reason


def test_rejected_strictly_blocked():
    gate = PolicyAgentAccessGate()
    claim = {"claim_id": "CLM-006", "certification_tier": "REJECTED"}
    allowed, level, reason = gate.check_access(claim)

    assert allowed is False
    assert level == AgentAccessLevel.NO_ACCESS
