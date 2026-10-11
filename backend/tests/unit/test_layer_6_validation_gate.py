"""
Unit tests for Layer 6: Validation Gate & Persistence.
Verifies:
1. 6-Dimensional Validation Gate Evaluators:
   - Source Match (Pass / Fail)
   - Completeness (Complete / Partial)
   - Meaning (Supported / Uncertain)
   - Scope (In / Out)
   - Time (Current / Stale)
   - Authority (Authoritative / Non-Authoritative)
2. Claim Lifecycle Decision Engine:
   - [APPROVE] High confidence & fully verified claims
   - [REVIEW] Uncertain meaning, partial fields, or non-authoritative items
   - [REJECT] Grounding failures or cross-tenant scope violations
3. Enterprise Claim Store & Pipeline:
   - Layer 6 Pipeline orchestration & metric calculation
   - PostgreSQL persistence (claims, evidence, validity, trust scores)
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest

from app.db.enums import ClaimStatus, SourceFamily, SourceIntent
from app.extraction.models import (
    CandidateClaim,
    ExtractionStrategyType,
    Layer5ExtractionResult,
)
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.validation_gate import (
    AuthorityEvaluator,
    AuthorityStatus,
    ClaimLifecycleDecision,
    ClaimLifecycleDecisionEngine,
    CompletenessEvaluator,
    CompletenessStatus,
    EnterpriseClaimStore,
    Layer6ValidationGatePipeline,
    MeaningEvaluator,
    MeaningStatus,
    ReviewStatus,
    ScopeEvaluator,
    ScopeStatus,
    SourceMatchEvaluator,
    SourceMatchStatus,
    TemporalValidityEvaluator,
    TimeStatus,
)


def _create_test_envelope(
    family: SourceFamily = SourceFamily.STRUCTURED,
    intent: SourceIntent = SourceIntent.OPERATIONAL_DATA,
    asset_id: str = "mongodb://cluster/Departmental/sampletests#1",
    captured_at: datetime | None = None,
) -> CanonicalSourceEnvelope:
    env_id = uuid.uuid4()
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    source_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    payload = {"test": True}

    return CanonicalSourceEnvelope(
        envelope_id=env_id,
        organization_id=org_id,
        source_id=source_id,
        asset_id=asset_id,
        source_family=family,
        source_intent=intent,
        native_format="json",
        source_version="v1.0",
        content_hash=EnvelopeFactory.calculate_hash(payload),
        raw_payload=payload,
        captured_at=captured_at or datetime.now(timezone.utc),
    )


def _create_test_candidate(
    envelope: CanonicalSourceEnvelope,
    claim_text: str = "Database users enforces MFA.",
    subject: str = "users",
    predicate: str = "enforces_mfa",
    object_: str = "true",
    evidence_span: str = "mfa: true",
    is_verified: bool = True,
    confidence: float = 0.95,
) -> CandidateClaim:
    c = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:unit1",
        asset_id=envelope.asset_id,
        claim_text=claim_text,
        subject=subject,
        predicate=predicate,
        object_=object_,
        evidence_text_span=evidence_span,
        extraction_strategy=ExtractionStrategyType.DETERMINISTIC_SCHEMA,
        confidence=confidence,
    )
    if is_verified:
        c.status = "verified"
        c.verification_plugin = "DatabaseRecordVerificationPlugin"
        c.verification_details = {"grounded": True, "field": predicate}
    else:
        c.status = "rejected"
        c.verification_plugin = None
    return c


# =========================================================================
# 1. 6-Dimensional Evaluator Tests
# =========================================================================

def test_source_match_evaluator():
    """Verifies that verified claims pass and unverified claims fail."""
    envelope = _create_test_envelope()
    valid_cand = _create_test_candidate(envelope, is_verified=True)
    res_valid = SourceMatchEvaluator.evaluate(valid_cand, envelope)
    assert res_valid.passed is True
    assert res_valid.status == SourceMatchStatus.PASS.value
    assert res_valid.score == 1.0

    invalid_cand = _create_test_candidate(envelope, is_verified=False)
    res_invalid = SourceMatchEvaluator.evaluate(invalid_cand, envelope)
    assert res_invalid.passed is False
    assert res_invalid.status == SourceMatchStatus.FAIL.value
    assert res_invalid.score == 0.0


def test_completeness_evaluator():
    """Verifies Subject-Predicate-Object and evidence span completeness."""
    envelope = _create_test_envelope()
    complete_cand = _create_test_candidate(envelope, subject="Server", predicate="runs", object_="Linux")
    res_comp = CompletenessEvaluator.evaluate(complete_cand)
    assert res_comp.passed is True
    assert res_comp.status == CompletenessStatus.COMPLETE.value
    assert res_comp.score == 1.0

    # Missing predicate
    partial_cand = _create_test_candidate(envelope, subject="Server", predicate="", object_="Linux")
    res_partial = CompletenessEvaluator.evaluate(partial_cand)
    assert res_partial.passed is False
    assert res_partial.status == CompletenessStatus.PARTIAL.value
    assert res_partial.score == 0.6


def test_meaning_evaluator():
    """Verifies supported entailment vs. speculative hedges."""
    envelope = _create_test_envelope()
    clear_cand = _create_test_candidate(envelope, claim_text="Production servers must enforce TLS 1.3.", confidence=0.95)
    res_clear = MeaningEvaluator.evaluate(clear_cand)
    assert res_clear.passed is True
    assert res_clear.status == MeaningStatus.SUPPORTED.value

    hedged_cand = _create_test_candidate(envelope, claim_text="Production servers might possibly use TLS 1.3 perhaps.", confidence=0.70)
    res_hedged = MeaningEvaluator.evaluate(hedged_cand)
    assert res_hedged.passed is False
    assert res_hedged.status == MeaningStatus.UNCERTAIN.value


def test_scope_evaluator():
    """Verifies tenant isolation and asset boundary enforcement."""
    envelope = _create_test_envelope(asset_id="db://prod/users")
    valid_cand = _create_test_candidate(envelope)
    res_in = ScopeEvaluator.evaluate(valid_cand, envelope)
    assert res_in.passed is True
    assert res_in.status == ScopeStatus.IN_SCOPE.value

    # Tampered / cross-asset candidate
    foreign_cand = _create_test_candidate(envelope)
    foreign_cand.asset_id = "db://competitor/foreign_asset"
    res_out = ScopeEvaluator.evaluate(foreign_cand, envelope)
    assert res_out.passed is False
    assert res_out.status == ScopeStatus.OUT_OF_SCOPE.value


def test_temporal_validity_evaluator():
    """Verifies freshness calculation within standard retention window."""
    now = datetime.now(timezone.utc)
    fresh_envelope = _create_test_envelope(captured_at=now - timedelta(days=5))
    cand_fresh = _create_test_candidate(fresh_envelope)
    res_fresh = TemporalValidityEvaluator.evaluate(cand_fresh, fresh_envelope)
    assert res_fresh.passed is True
    assert res_fresh.status == TimeStatus.CURRENT.value
    assert res_fresh.score >= 0.8

    stale_envelope = _create_test_envelope(captured_at=now - timedelta(days=250))
    cand_stale = _create_test_candidate(stale_envelope)
    res_stale = TemporalValidityEvaluator.evaluate(cand_stale, stale_envelope)
    assert res_stale.passed is False
    assert res_stale.status == TimeStatus.STALE.value
    assert res_stale.score == 0.4


def test_authority_evaluator_hierarchy():
    """Verifies authority tier hierarchy (Tier 1 vs. Tier 2 vs. Tier 3)."""
    # Tier 1
    policy_env = _create_test_envelope(family=SourceFamily.DOCUMENT, intent=SourceIntent.GOVERNANCE_POLICY)
    res_tier1 = AuthorityEvaluator.evaluate(policy_env)
    assert res_tier1.passed is True
    assert res_tier1.score == 1.0
    assert res_tier1.status == AuthorityStatus.AUTHORITATIVE.value

    # Tier 2
    factual_env = _create_test_envelope(family=SourceFamily.DOCUMENT, intent=SourceIntent.FACTUAL_KNOWLEDGE)
    res_tier2 = AuthorityEvaluator.evaluate(factual_env)
    assert res_tier2.passed is True
    assert res_tier2.score == 0.85

    # Tier 3
    chat_env = _create_test_envelope(family=SourceFamily.CONVERSATION, intent=SourceIntent.PROPOSALS_DISCUSSIONS)
    res_tier3 = AuthorityEvaluator.evaluate(chat_env)
    assert res_tier3.passed is False
    assert res_tier3.score == 0.50
    assert res_tier3.status == AuthorityStatus.NON_AUTHORITATIVE.value


# =========================================================================
# 2. Claim Lifecycle Decision Engine Tests
# =========================================================================

def test_decision_engine_approve_lifecycle():
    """Candidate with clean evidence, high authority and high confidence is auto-approved."""
    envelope = _create_test_envelope(family=SourceFamily.STRUCTURED, intent=SourceIntent.OPERATIONAL_DATA)
    candidate = _create_test_candidate(envelope, is_verified=True, confidence=0.98)

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.APPROVE
    assert gate_eval.composite_trust_score >= 0.85
    assert "APPROVED" in gate_eval.decision_reason
    assert gate_eval.review_trigger.status == ReviewStatus.NO_REVIEW_NEEDED.value


def test_decision_engine_review_lifecycle():
    """Candidate from discussions or with speculative hedges is escalated to human review."""
    envelope = _create_test_envelope(family=SourceFamily.CONVERSATION, intent=SourceIntent.PROPOSALS_DISCUSSIONS)
    candidate = _create_test_candidate(envelope, is_verified=True, confidence=0.85)

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW
    assert "REVIEW" in gate_eval.decision_reason
    assert gate_eval.review_trigger.status == ReviewStatus.REVIEW_REQUIRED.value


def test_decision_engine_reject_lifecycle():
    """Candidate failing source match is hard-rejected."""
    envelope = _create_test_envelope()
    candidate = _create_test_candidate(envelope, is_verified=False)

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert "REJECTED" in gate_eval.decision_reason
    assert gate_eval.source_match.passed is False


# =========================================================================
# 3. Layer 6 Pipeline Orchestration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_layer_6_pipeline_processing():
    """Executes Layer 6 pipeline over a simulated Layer 5 extraction result."""
    envelope = _create_test_envelope()
    c1 = _create_test_candidate(envelope, claim_text="Rule 1: All passwords must be complex.", is_verified=True)
    c2 = _create_test_candidate(envelope, claim_text="Rule 2: Passwords might be rotated maybe.", is_verified=True, confidence=0.6)
    c3 = _create_test_candidate(envelope, claim_text="Rule 3: Fabricated ungrounded claim.", is_verified=False)

    l5_result = Layer5ExtractionResult(
        envelope_id=envelope.envelope_id,
        asset_id=envelope.asset_id,
        total_evidence_units_received=3,
        candidates_discovered=3,
        claims_extracted=3,
        claims_verified=2,
        claims_rejected=1,
        completeness_score=1.0,
        candidates=[c1, c2, c3],
    )

    pipeline = Layer6ValidationGatePipeline(persist_to_db=False)
    result = await pipeline.process_extraction_result(envelope, l5_result)

    assert result.total_candidates_evaluated == 3
    assert result.claims_approved == 1  # c1
    assert result.claims_queued_for_review == 1  # c2 (hedged)
    assert result.claims_rejected == 1  # c3 (unverified)
    assert result.average_trust_score > 0.0
    assert len(result.evaluations) == 3


# =========================================================================
# 4. Enterprise Claim Store Database Persistence Tests
# =========================================================================

@pytest.mark.asyncio
async def test_enterprise_claim_store_persistence():
    """Verifies that EnterpriseClaimStore saves claims, evidence, and trust scores to PostgreSQL."""
    envelope = _create_test_envelope()
    c = _create_test_candidate(envelope, is_verified=True)

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(c, envelope)
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.APPROVE

    persisted_ids = await EnterpriseClaimStore.persist_evaluations(
        evaluations=[gate_eval],
        candidates_map={c.candidate_id: c},
        envelope=envelope,
    )

    assert len(persisted_ids) == 1
    assert gate_eval.persisted_claim_id == persisted_ids[0]
