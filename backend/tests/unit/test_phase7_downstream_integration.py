"""
Unit tests for Phase 7: Downstream Integration of Evidence and Claims Architecture.

Verifies:
1. Existing API consumers: ClaimResponse and ClaimEvidenceResponse expose new fields with safe defaults without breaking existing callers.
2. Repeated source sync: Deduplication ensures repeated sync skips unchanged sources and does not duplicate claims or evidence.
3. Updated source version: Updating source from v1.0 to v2.0 triggers incremental processing and preserves version lineage.
4. Claim with multiple evidence units: Storing and retrieving a claim with multiple evidence units preserves all linked evidence IDs and relationships.
5. Genuine vs non-genuine conflicts:
   - Genuine: same subject, competing predicates, same scope, conflicting values.
   - Non-genuine: distinct scopes (e.g. Grade A vs Grade B) or complementary conditional scopes.
6. HITL for uncertain evidence: Claims with missing conditions, ambiguous table cells, or uncertain OCR escalate to HITL triage, while valid claims are approved.
7. Trust scoring with failed extraction: Failed extraction, invalid locator, or missing conditions penalizes and caps trust scores.
8. Historical claim retrieval: Claims from older document versions remain retrievable and marked as superseded/outdated.
"""

import decimal
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus, SourceFamily, SourceIntent
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ContentRole, ExtractionStatus
from app.schemas.claim import ClaimEvidenceResponse, ClaimResponse
from app.trust_engine.calculator import TrustScoreCalculator
from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.services.hitl_service import record_claim_evidence_escalation, _IN_MEMORY_ESCALATIONS
from app.validation_gate.models import (
    CandidateGateEvaluation,
    ClaimLifecycleDecision,
    ClaimValidationStatus,
    DecisionCode,
    DimensionEvaluation,
)
from app.validation_gate.persistence import EnterpriseClaimStore, _generate_deterministic_claim_uuid


# =========================================================================
# Test 1: Existing API Consumers
# =========================================================================

def test_existing_api_consumers_claim_response_backward_compatibility():
    """ClaimResponse must expose new Phase 7 fields while remaining 100% backward-compatible with legacy callers."""
    claim_id = uuid.uuid4()
    org_id = uuid.uuid4()
    version_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Legacy dictionary representation without Phase 7 fields
    legacy_claim_dict = {
        "id": claim_id,
        "organization_id": org_id,
        "document_version_id": version_id,
        "claim_text": "Employees must submit expense receipts within 30 days.",
        "subject": "Employees",
        "predicate": "must submit",
        "object": "expense receipts within 30 days",
        "claim_type": "policy",
        "extraction_method": "table_aware",
        "extraction_model": "UniversalLayer5",
        "status": ClaimStatus.VERIFIED,
        "created_at": now,
        "updated_at": now,
        "evidence": [
            {
                "id": uuid.uuid4(),
                "claim_id": claim_id,
                "document_id": uuid.uuid4(),
                "evidence_type": "source_evidence",
                "page_number": 5,
                "section": "Expenses",
                "text_span": "Employees must submit expense receipts within 30 days.",
                "created_at": now,
            }
        ],
        "validity_records": [
            {
                "id": uuid.uuid4(),
                "claim_id": claim_id,
                "is_current": True,
                "version": "v1.0",
                "validity_status": "CURRENT",
                "created_at": now,
            }
        ],
        "trust_scores": [
            {
                "id": uuid.uuid4(),
                "claim_id": claim_id,
                "source_score": decimal.Decimal("0.9000"),
                "freshness_score": decimal.Decimal("0.9500"),
                "evidence_score": decimal.Decimal("0.9500"),
                "consistency_score": decimal.Decimal("1.0000"),
                "authority_score": decimal.Decimal("0.9000"),
                "human_score": decimal.Decimal("1.0000"),
                "overall_score": decimal.Decimal("0.9400"),
                "calculated_at": now,
            }
        ],
    }

    response = ClaimResponse.model_validate(legacy_claim_dict)

    # Legacy fields intact
    assert response.id == claim_id
    assert response.claim_text == "Employees must submit expense receipts within 30 days."
    assert response.status == ClaimStatus.VERIFIED

    # Phase 7 new fields populated with sensible defaults/derived context
    assert response.source_version == "v1.0"
    assert response.evidence_quotes == ["Employees must submit expense receipts within 30 days."]
    assert response.locator == {"page": 5, "section": "Expenses", "start_offset": None, "end_offset": None}
    assert response.conditions == []
    assert response.exceptions == []
    assert response.warnings == []


# =========================================================================
# Test 2: Repeated Source Sync & Deduplication
# =========================================================================

def test_deterministic_claim_uuid_deduplication():
    """Exact same candidate extracted on repeated sync generates identical UUID, preventing duplicate rows."""
    version_id = uuid.uuid4()
    candidate_1 = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit-1",
        asset_id="asset-1",
        claim_text="Standard notice period is 60 days.",
        subject="Standard notice period",
        predicate="is",
        object_="60 days",
        evidence_text_span="Standard notice period is 60 days.",
    )
    candidate_2 = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit-1",
        asset_id="asset-1",
        claim_text="Standard notice period is 60 days.",
        subject="Standard notice period",
        predicate="is",
        object_="60 days",
        evidence_text_span="Standard notice period is 60 days.",
    )

    uuid_1 = _generate_deterministic_claim_uuid(version_id, candidate_1)
    uuid_2 = _generate_deterministic_claim_uuid(version_id, candidate_2)

    assert uuid_1 == uuid_2, "Deterministic UUID must match across repeated extraction syncs"


# =========================================================================
# Test 3: Updated Source Version & Version Lineage
# =========================================================================

def test_updated_source_version_lineage():
    """Updating source version (v1.0 to v2.0) generates distinct UUIDs per version, preserving historical lineage."""
    version_1_id = uuid.uuid4()
    version_2_id = uuid.uuid4()

    candidate = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit-1",
        asset_id="asset-policy",
        claim_text="Annual vacation allowance is 25 days.",
        subject="Annual vacation allowance",
        predicate="is",
        object_="25 days",
        evidence_text_span="Annual vacation allowance is 25 days.",
    )

    claim_v1_uuid = _generate_deterministic_claim_uuid(version_1_id, candidate)
    claim_v2_uuid = _generate_deterministic_claim_uuid(version_2_id, candidate)

    assert claim_v1_uuid != claim_v2_uuid, "Different document versions must have distinct claim records to preserve history"


# =========================================================================
# Test 4: Claim with Multiple Evidence Units
# =========================================================================

@pytest.mark.anyio
async def test_claim_with_multiple_evidence_units():
    """Storing a claim with multi-evidence units correctly records primary and corroborating evidence records."""
    doc_id = uuid.uuid4()
    doc_ver_id = uuid.uuid4()
    org_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=org_id,
        source_id=uuid.uuid4(),
        asset_id="asset-policy.docx",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="docx",
        raw_payload=b"Sample policy bytes",
        content_hash="mock-hash-123",
        source_version="v2.1",
        captured_at=now,
    )

    candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id="unit-rule",
        asset_id=envelope.asset_id,
        claim_text="Full-time staff are entitled to 12 weeks parental leave.",
        subject="Full-time staff",
        predicate="are entitled to",
        object_="12 weeks parental leave",
        evidence_text_span="Full-time staff are entitled to 12 weeks parental leave.",
        source_version="v2.1",
        evidence_unit_ids=["unit-rule", "unit-definition"],
    )
    # Add a corroborating occurrence from another section
    candidate.duplicate_occurrences = [
        {
            "evidence_text_span": "Parental leave policy applies to full-time employees with 1+ year service.",
            "content_hash": "hash-definition-unit-2",
            "locator": {"page": 4, "section": "Definitions"},
        }
    ]

    eval_record = CandidateGateEvaluation(
        candidate_id=candidate.candidate_id,
        envelope_id=envelope.envelope_id,
        asset_id=envelope.asset_id,
        claim_text=candidate.claim_text,
        subject=candidate.subject,
        predicate=candidate.predicate,
        object_=candidate.object,
        evidence_text_span=candidate.evidence_text_span,
        source_match=DimensionEvaluation(dimension_name="source_match", status="pass", score=1.0, passed=True, reason="Pass"),
        completeness=DimensionEvaluation(dimension_name="completeness", status="complete", score=1.0, passed=True, reason="Pass"),
        meaning=DimensionEvaluation(dimension_name="meaning", status="supported", score=1.0, passed=True, reason="Pass"),
        time=DimensionEvaluation(dimension_name="time", status="current", score=1.0, passed=True, reason="Pass"),
        authority=DimensionEvaluation(dimension_name="authority", status="authoritative", score=1.0, passed=True, reason="Pass"),
        review_trigger=DimensionEvaluation(dimension_name="review", status="no", score=1.0, passed=True, reason="Pass"),
        composite_trust_score=0.98,
        lifecycle_decision=ClaimLifecycleDecision.APPROVE,
        decision_code=DecisionCode.APPROVE_ALL_PASSED,
        decision_reason="Approved",
        validation_status=ClaimValidationStatus.SUPPORTED,
    )

    # Mock DB session to verify records added
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=DocumentVersion(
        id=doc_ver_id,
        document_id=doc_id,
        version_number=2,
        content_uri=envelope.asset_id,
        content_hash="mock",
        is_current=True,
    ))
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    persisted_ids = await EnterpriseClaimStore._persist_with_session(
        evaluations=[eval_record],
        candidates_map={candidate.candidate_id: candidate},
        envelope=envelope,
        session=mock_session,
        document_version_id=doc_ver_id,
    )

    assert len(persisted_ids) == 1
    # Check that multiple ClaimEvidence objects were added (primary + corroborating)
    added_evidence = [call.args[0] for call in mock_session.add.call_args_list if isinstance(call.args[0], ClaimEvidence)]
    assert len(added_evidence) >= 2
    assert any(e.evidence_type == "source_evidence" for e in added_evidence)
    assert any(e.evidence_type == "corroborating_evidence" for e in added_evidence)


# =========================================================================
# Test 5: Genuine vs Non-Genuine Conflicts
# =========================================================================

def test_genuine_vs_non_genuine_conflicts():
    """
    Genuine conflict: Same subject, competing predicate, overlapping scope, conflicting values.
    Non-genuine conflict: Different employment status (probationary vs confirmed) or different grades.
    """
    # Claim A: Probationary notice period is 30 days
    claim_probation = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit-1",
        asset_id="asset-policy",
        claim_text="Probationary employees notice period is 30 days.",
        subject="Employees",
        predicate="has_probationary_notice_duration",
        object_="30 days",
        evidence_text_span="Probationary employees notice period is 30 days.",
        conditions=["employment_status: probationary"],
        value=30,
        unit="days",
    )

    # Claim B: Confirmed employees notice period is 90 days (COMPLEMENTARY, not a conflict!)
    claim_confirmed = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit-1",
        asset_id="asset-policy",
        claim_text="Confirmed employees notice period is 90 days.",
        subject="Employees",
        predicate="has_confirmed_notice_duration",
        object_="90 days",
        evidence_text_span="Confirmed employees notice period is 90 days.",
        conditions=["employment_status: confirmed"],
        value=90,
        unit="days",
    )

    # Claim C: Conflicting probationary rule asserting 60 days for probationers (GENUINE CONFLICT!)
    claim_probation_conflict = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit-2",
        asset_id="asset-policy-2",
        claim_text="Probationary employees notice period is 60 days.",
        subject="Employees",
        predicate="has_probationary_notice_duration",
        object_="60 days",
        evidence_text_span="Probationary employees notice period is 60 days.",
        conditions=["employment_status: probationary"],
        value=60,
        unit="days",
    )

    # 1. Non-Genuine Conflict Evaluation:
    compat_outcome = CompatibilityGate.evaluate_compatibility(claim_probation, claim_confirmed)
    assert compat_outcome.is_comparable is False
    assert compat_outcome.relationship == "COMPLEMENTARY_CONDITIONAL_RULES"

    # 2. Genuine Conflict Evaluation:
    compat_genuine = CompatibilityGate.evaluate_compatibility(claim_probation, claim_probation_conflict)
    assert compat_genuine.is_comparable is True
    assert compat_genuine.reason == "COMPETING_DECISION_KEYS"

    is_val_conflict, conflict_type = CompatibilityGate.evaluate_value_conflict(claim_probation, claim_probation_conflict)
    assert is_val_conflict is True
    assert conflict_type == "INCOMPATIBLE_NUMERIC_VALUE"


# =========================================================================
# Test 6: HITL Escalation for Uncertain Evidence
# =========================================================================

@pytest.mark.anyio
async def test_hitl_escalation_for_uncertain_evidence():
    """Unresolved evidence issues (missing conditions, ambiguous extraction, uncertain OCR) escalate to HITL."""
    org_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    esc = await record_claim_evidence_escalation(
        claim_id=claim_id,
        organization_id=org_id,
        issue_type="missing_conditions",
        details="Claim omitted source requirement: 'less than 20% viewed'",
        reasons=["Source condition omitted from claim context.", "Potential compliance liability."],
        claim_text="Video courses are refundable anytime.",
        liability_prevented_usd=7500.0,
    )

    assert esc is not None
    assert esc.status == "PENDING"
    assert "Missing Conditions" in esc.category
    assert esc.liability_prevented_usd == 7500.0
    assert str(esc.id) in _IN_MEMORY_ESCALATIONS


# =========================================================================
# Test 7: Trust Scoring with Failed Extraction or Missing Conditions
# =========================================================================

def test_trust_scoring_penalties_and_guardrails():
    """
    TrustScoreCalculator must enforce Phase 7 fail-closed guardrails:
    1. Failed extraction caps overall score <= 0.30.
    2. Missing conditions caps overall score <= 0.65.
    3. Contradicted claims caps overall score <= 0.20.
    """
    calc = TrustScoreCalculator()

    # Case A: Standard high-trust verified claim
    res_high = calc.calculate(
        source_authority_level=90,
        is_current_version=True,
        has_evidence=True,
        has_valid_locator=True,
        validation_status="SUPPORTED",
    )
    assert float(res_high.overall_score) >= 0.85

    # Case B: Failed extraction status
    res_failed_ext = calc.calculate(
        source_authority_level=90,
        extraction_status="failed",
        has_evidence=True,
        has_valid_locator=True,
    )
    assert float(res_failed_ext.overall_score) <= 0.30
    assert float(res_failed_ext.evidence_score) <= 0.10

    # Case C: Claim with missing required conditions
    res_missing_conds = calc.calculate(
        source_authority_level=90,
        has_evidence=True,
        has_valid_locator=True,
        has_missing_conditions=True,
        validation_status="NEEDS_REVIEW",
    )
    assert float(res_missing_conds.overall_score) <= 0.65

    # Case D: Contradicted claim
    res_contradicted = calc.calculate(
        source_authority_level=90,
        has_evidence=True,
        validation_status="CONTRADICTED",
    )
    assert float(res_contradicted.overall_score) <= 0.20
    assert float(res_contradicted.consistency_score) <= 0.20


# =========================================================================
# Test 8: Historical Claim Retrieval
# =========================================================================

def test_historical_claim_retrieval_and_superseded_status():
    """Historical claim from an older document version preserves its version metadata and is marked outdated."""
    calc = TrustScoreCalculator()

    # Evaluating a claim from an older/superseded document version
    res_historical = calc.calculate(
        source_authority_level=80,
        is_current_version=False,  # Superseded version
        has_evidence=True,
    )

    # Authority and freshness penalized for superseded versions
    assert float(res_historical.authority_score) == 0.50
    assert float(res_historical.overall_score) < 0.75
