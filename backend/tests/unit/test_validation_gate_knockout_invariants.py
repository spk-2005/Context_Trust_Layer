"""
Unit tests for Layer 6 Validation Gate Knockout Invariants.

Verifies the non-compensable safety properties of ClaimLifecycleDecisionEngine:
1. Source match failure -> Hard REJECT (even with 100% authority & max score).
2. Scope failure -> Hard REJECT (even with 100% authority & max score).
3. Meaning explicitly unsupported (e.g. Subject-Evidence mismatch) -> Hard REJECT.
4. Meaning ambiguous or partial -> Escalate to REVIEW, not REJECT.
5. All hard checks pass, but composite trust score < 0.88 -> Escalate to REVIEW.
6. Exact threshold boundary (0.88) -> Auto-APPROVE when all dimensions pass.
7. Discretionary right / permission misclassified as OBLIGATION -> Never auto-approve (routes to REVIEW).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.db.enums import SourceFamily, SourceIntent
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.validation_gate import (
    ClaimLifecycleDecision,
    ClaimLifecycleDecisionEngine,
    DecisionCode,
    MeaningStatus,
    ReviewStatus,
    ScopeStatus,
    SourceMatchStatus,
)


def _build_maximal_authority_envelope(
    organization_id: uuid.UUID | None = None,
    asset_id: str = "file:///governance/policies/security_policy.pdf",
) -> CanonicalSourceEnvelope:
    """Creates a Tier 1 (100% Authority, 100% Time validity) canonical envelope."""
    env_id = uuid.uuid4()
    org_id = organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
    payload = {"source": "Enterprise Information Security Policy v4.0", "active": True}

    return CanonicalSourceEnvelope(
        envelope_id=env_id,
        organization_id=org_id,
        source_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        asset_id=asset_id,
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,  # Tier 1 Authority -> 1.0 score
        native_format="pdf",
        source_version="v4.0",
        content_hash=EnvelopeFactory.calculate_hash(payload),
        raw_payload=payload,
        captured_at=datetime.now(timezone.utc),  # Fresh capture -> 1.0 score
    )


def _build_candidate(
    envelope: CanonicalSourceEnvelope,
    claim_text: str = "Employees must return all company equipment upon separation.",
    subject: str = "Employees",
    predicate: str = "must_return_company_property",
    object_: str = "all company equipment",
    evidence_span: str = "Employees must return all company equipment upon separation.",
    is_verified: bool = True,
    confidence: float = 0.98,
    modality: str = "OBLIGATION",
) -> CandidateClaim:
    """Creates a candidate claim linked to the test envelope."""
    c = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:unit_1",
        asset_id=envelope.asset_id,
        claim_text=claim_text,
        subject=subject,
        predicate=predicate,
        object_=object_,
        evidence_text_span=evidence_span,
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=confidence,
        modality=modality,
    )
    if is_verified:
        c.status = "verified"
        c.verification_plugin = "DocumentPlugin"
        c.verification_details = {"hash_verified": True, "evidence_offset": 42}
    else:
        c.status = "rejected"
        c.verification_plugin = None
        c.verification_details = {}
    return c


# =========================================================================
# Invariant Test 1: Grounding Failure Knockout
# =========================================================================

def test_source_match_failure_knockout_rejected_despite_max_authority():
    """
    INVARIANT 1:
    Even with 100% Authority, fresh Time, and valid S-P-O structure,
    a failure in Layer 5 Source Match (unverified candidate) MUST trigger hard REJECT.
    High authority cannot average away a grounding failure.
    """
    envelope = _build_maximal_authority_envelope()
    candidate = _build_candidate(envelope, is_verified=False, confidence=0.98)

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)

    assert gate_eval.source_match.passed is False
    assert gate_eval.source_match.status == SourceMatchStatus.FAIL.value
    assert gate_eval.authority.score == 1.0  # Max authority confirmed
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert gate_eval.decision_code == DecisionCode.REJECT_GROUNDING_FAILED
    assert "REJECTED: Grounding failure" in gate_eval.decision_reason


# =========================================================================
# Invariant Test 2: Scope Violation Knockout
# =========================================================================

def test_scope_violation_knockout_rejected_despite_max_authority():
    """
    INVARIANT 2:
    A candidate referencing an unapproved asset or alien envelope MUST trigger hard REJECT,
    even if it has clean verification and maximum authority.
    """
    envelope = _build_maximal_authority_envelope()
    candidate = _build_candidate(envelope, is_verified=True, confidence=0.98)
    # Tamper asset_id to simulate cross-tenant or out-of-scope asset contamination
    candidate.asset_id = "file:///alien_tenant/secrets/confidential.pdf"

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)

    assert gate_eval.scope_eval.passed is False
    assert gate_eval.scope_eval.status == ScopeStatus.OUT_OF_SCOPE.value
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert gate_eval.decision_code == DecisionCode.REJECT_SCOPE_VIOLATION
    assert "REJECTED: Scope violation" in gate_eval.decision_reason


# =========================================================================
# Invariant Test 3: Meaning Unsupported Knockout (Subject Mismatch)
# =========================================================================

def test_unsupported_meaning_knockout_rejected_despite_high_score():
    """
    INVARIANT 3:
    When candidate asserted subject has zero semantic grounding in the evidence span,
    MeaningEvaluator reports UNSUPPORTED, which MUST trigger hard REJECT.
    """
    envelope = _build_maximal_authority_envelope()
    # Subject is fabricated, completely unrelated to evidence span
    candidate = _build_candidate(
        envelope,
        claim_text="Quantum Cloud Hypervisor must return all company equipment.",
        subject="Quantum Cloud Hypervisor",
        predicate="return",
        object_="all company equipment",
        evidence_span="Employees must return all company equipment upon separation.",
        is_verified=True,
        confidence=0.95,
    )

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)

    assert gate_eval.meaning.passed is False
    assert gate_eval.meaning.status == MeaningStatus.UNSUPPORTED.value
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert gate_eval.decision_code == DecisionCode.REJECT_SEMANTIC_MISMATCH
    assert "REJECTED: Semantic grounding failure" in gate_eval.decision_reason


# =========================================================================
# Invariant Test 4: Ambiguous/Partial Meaning Routes to REVIEW
# =========================================================================

def test_ambiguous_meaning_routes_to_review():
    """
    INVARIANT 4:
    Speculative hedges ('might', 'maybe', 'perhaps') do not cause hard REJECT,
    but MUST escalate to human REVIEW.
    """
    envelope = _build_maximal_authority_envelope()
    candidate = _build_candidate(
        envelope,
        claim_text="Employees might possibly return all company equipment maybe.",
        subject="Employees",
        predicate="must_return_company_property",
        object_="all company equipment",
        evidence_span="Employees must return all company equipment upon separation.",
        is_verified=True,
        confidence=0.90,
    )

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)

    assert gate_eval.meaning.passed is False
    assert gate_eval.meaning.status == MeaningStatus.UNCERTAIN.value
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW
    assert gate_eval.decision_code == DecisionCode.REVIEW_UNCERTAIN_MEANING
    assert gate_eval.review_trigger.status == ReviewStatus.REVIEW_REQUIRED.value
    assert "REVIEW: Human review recommended" in gate_eval.decision_reason


# =========================================================================
# Invariant Test 5: Sub-Threshold Score (0.87) Routes to REVIEW
# =========================================================================

def test_sub_threshold_trust_score_0_87_routes_to_review():
    """
    INVARIANT 5:
    When all hard checks pass, but composite confidence/trust score falls
    below the 0.88 auto-approval threshold (e.g. candidate confidence 0.87),
    the lifecycle decision MUST be REVIEW, not REJECT and not APPROVE.
    """
    envelope = _build_maximal_authority_envelope()
    candidate = _build_candidate(
        envelope,
        is_verified=True,
        confidence=0.87,  # Below 0.88 threshold
    )

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)

    assert gate_eval.source_match.passed is True
    assert gate_eval.scope_eval.passed is True
    # Meaning flags sub-threshold confidence (< 0.88)
    assert gate_eval.meaning.passed is False
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW
    assert gate_eval.decision_code == DecisionCode.REVIEW_UNCERTAIN_MEANING
    assert "REVIEW: Human review recommended" in gate_eval.decision_reason


# =========================================================================
# Invariant Test 6: Boundary Check at Exactly 0.88
# =========================================================================

def test_exact_threshold_boundary_0_88_auto_approves():
    """
    INVARIANT 6:
    When candidate has confidence 0.88 (meeting the exact threshold)
    with clean S-P-O and Tier 1 authority envelope, the decision MUST be APPROVE.
    """
    envelope = _build_maximal_authority_envelope()
    candidate = _build_candidate(
        envelope,
        is_verified=True,
        confidence=0.88,
    )

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)

    assert gate_eval.source_match.passed is True
    assert gate_eval.meaning.passed is True
    assert gate_eval.composite_trust_score >= 0.88
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.APPROVE
    assert gate_eval.decision_code == DecisionCode.APPROVE_ALL_PASSED
    assert "APPROVED" in gate_eval.decision_reason


# =========================================================================
# Invariant Test 7: Discretionary Right Misclassified as Obligation
# =========================================================================

def test_discretionary_right_misclassified_as_obligation_fails_auto_approve():
    """
    INVARIANT 7:
    If a discretionary company right / permission ('Wingify holds the right to recover')
    is mistakenly classified with modality='OBLIGATION', MeaningEvaluator must detect
    the deontic mismatch against the underlying evidence, preventing auto-approval.
    """
    envelope = _build_maximal_authority_envelope()
    candidate = _build_candidate(
        envelope,
        claim_text="Wingify holds the right to recover short notice period.",
        subject="Wingify",
        predicate="recover",
        object_="short notice period",
        evidence_span="Wingify holds the right to recover short notice period amounts.",
        is_verified=True,
        confidence=0.95,
        modality="OBLIGATION",  # Wrong modality! Evidence only grants a discretionary right (PERMISSION)
    )

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)

    assert gate_eval.meaning.passed is False
    assert gate_eval.meaning.status == MeaningStatus.UNCERTAIN.value
    assert "Deontic mismatch" in gate_eval.meaning.reason
    # MUST NOT auto-approve!
    assert gate_eval.lifecycle_decision != ClaimLifecycleDecision.APPROVE
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW
    assert gate_eval.decision_code == DecisionCode.REVIEW_UNCERTAIN_MEANING
