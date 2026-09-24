import uuid
from datetime import datetime, timezone, timedelta
import pytest
from types import SimpleNamespace

from app.conflict_engine.precedence_engine import PrecedenceEngine, PrecedenceDecision
from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.llm.schemas import ContradictionResult


def make_mock_claim(
    text: str,
    subject: str = "Refund Policy",
    version_num: int = 1,
    doc_id: uuid.UUID | None = None,
    overall_trust: float = 0.85,
    authority_level: int = 75,
    is_current: bool = True,
    valid_until: datetime | None = None,
):
    cid = uuid.uuid4()
    doc_uuid = doc_id or uuid.uuid4()
    
    # Mock document version
    doc_version = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=doc_uuid,
        version_number=version_num,
        document=SimpleNamespace(
            id=doc_uuid,
            source=SimpleNamespace(authority_level=authority_level),
        ),
    )
    
    # Mock trust scores
    trust_scores = [SimpleNamespace(overall_score=overall_trust)]
    
    # Mock validity
    validity_records = [
        SimpleNamespace(
            is_current=is_current,
            valid_until=valid_until,
        )
    ]
    
    claim = SimpleNamespace(
        id=cid,
        claim_text=text,
        subject=subject,
        predicate="stipulates",
        object_value="",
        status=ClaimStatus.CANDIDATE,
        document_version=doc_version,
        trust_scores=trust_scores,
        validity_records=validity_records,
        evidence=[],
        authority_level=authority_level,
    )
    return claim


def test_rule1_canonical_deduplication():
    """Identical policy statements are deduplicated in favor of canonical master claim."""
    claim_a = make_mock_claim("Enterprise annual contracts require 30-day notice for refund.", overall_trust=0.92)
    claim_b = make_mock_claim("  Enterprise annual contracts require 30-day notice for refund.  ", overall_trust=0.81)

    decision = PrecedenceEngine.evaluate_precedence(claim_a, claim_b)
    assert decision.is_auto_resolved is True
    assert decision.precedence_rule == "CANONICAL_DEDUPLICATION"
    assert decision.winner_claim_id == claim_a.id
    assert decision.loser_claim_id == claim_b.id


def test_rule2_temporal_version_lineage():
    """Newer document version (v2.0) supersedes legacy version (v1.0)."""
    common_doc_id = uuid.uuid4()
    claim_v1 = make_mock_claim("Refund window is 14 calendar days.", version_num=1, doc_id=common_doc_id)
    claim_v2 = make_mock_claim("Refund window is 30 calendar days.", version_num=2, doc_id=common_doc_id)

    decision = PrecedenceEngine.evaluate_precedence(claim_v1, claim_v2)
    assert decision.is_auto_resolved is True
    assert decision.precedence_rule == "TEMPORAL_VERSION_PRECEDENCE"
    assert decision.winner_claim_id == claim_v2.id
    assert decision.loser_claim_id == claim_v1.id
    assert "v2.0 supersedes legacy version v1.0" in decision.reasoning


def test_rule3_temporal_validity_dates():
    """Expired validity date automatically concedes precedence to active policy."""
    now = datetime.now(timezone.utc)
    expired_claim = make_mock_claim("Processing fee is $50.", is_current=False, valid_until=now - timedelta(days=30))
    active_claim = make_mock_claim("Processing fee is $0.", is_current=True, valid_until=now + timedelta(days=365))

    decision = PrecedenceEngine.evaluate_precedence(expired_claim, active_claim)
    assert decision.is_auto_resolved is True
    assert decision.precedence_rule == "TEMPORAL_EXPIRATION_PRECEDENCE"
    assert decision.winner_claim_id == active_claim.id
    assert decision.loser_claim_id == expired_claim.id


def test_rule3_linguistic_obsolescence():
    """Explicit legacy / deprecated markers concede precedence to current governing policy."""
    legacy_claim = make_mock_claim("LEGACY EVIDENCE: Maximum reimbursement is $5,000 under archived 2021 guidelines.")
    current_claim = make_mock_claim("CURRENT EVIDENCE: Maximum reimbursement is $15,000 under active policy.")

    decision = PrecedenceEngine.evaluate_precedence(legacy_claim, current_claim)
    assert decision.is_auto_resolved is True
    assert decision.precedence_rule == "TEMPORAL_OBSOLESCENCE"
    assert decision.winner_claim_id == current_claim.id
    assert decision.loser_claim_id == legacy_claim.id


def test_rule4_source_authority_hierarchy():
    """Corporate governing authority (90%) overrides departmental guidelines (70%)."""
    dept_claim = make_mock_claim("Expenses over $100 require manager approval.", authority_level=65)
    corp_claim = make_mock_claim("Expenses over $500 require VP approval under Global Governance Policy.", authority_level=90)

    decision = PrecedenceEngine.evaluate_precedence(dept_claim, corp_claim)
    assert decision.is_auto_resolved is True
    assert decision.precedence_rule == "AUTHORITY_HIERARCHY_PRECEDENCE"
    assert decision.winner_claim_id == corp_claim.id
    assert decision.loser_claim_id == dept_claim.id


def test_rule5_lex_specialis_exception():
    """Specific enterprise tier exception is recognized as compatible with standard policy."""
    standard_claim = make_mock_claim(
        "Standard automated settlement window is 5 business days for all users.",
        subject="standard settlement",
        authority_level=75,
    )
    enterprise_claim = make_mock_claim(
        "Enterprise tier clients receive 24-hour expedited settlement upon VP approval.",
        subject="enterprise tier",
        authority_level=75,
    )

    decision = PrecedenceEngine.evaluate_precedence(standard_claim, enterprise_claim)
    assert decision.is_auto_resolved is True
    assert decision.is_compatible_exception is True
    assert decision.precedence_rule == "LEX_SPECIALIS_EXCEPTION"


def test_ambiguous_conflict_requires_human_review():
    """Genuinely ambiguous corporate contradictions cannot be deterministically resolved and are queued."""
    claim_a = make_mock_claim("Refunds must be requested within 30 days of invoice.", authority_level=75)
    claim_b = make_mock_claim("Refunds must be requested within 45 days of invoice.", authority_level=75)

    decision = PrecedenceEngine.evaluate_precedence(claim_a, claim_b)
    assert decision.is_auto_resolved is False
    assert "human" in decision.reasoning.lower() or "conflicting" in decision.reasoning.lower()
