"""
Regression and Invariant Test Suite for Claim-Key Aware Conflict Engine.

Tests:
1. Notice Period Matrix Complementarity: Grade A-E probation vs confirmed claims are non-conflicting.
2. Genuine Numeric Contradiction: Identical subject, predicate, and condition with different values must trigger CONFLICT.
3. Version Supersession: Newer document version supersedes older version (SUPERSEDED / OUTDATED), not CONFLICT.
4. Orthogonal Predicates: Different operational actions on the same subject must not conflict.
"""

import uuid
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
import pytest

from app.conflict_engine.compatibility_gate import CompatibilityGate, CompatibilityOutcome
from app.conflict_engine.normalizer import ClaimNormalizer
from app.conflict_engine.precedence_engine import PrecedenceEngine
from app.db.enums import ClaimStatus
from app.db.models.claim import Claim


def _create_mock_claim(
    claim_text: str,
    subject: str,
    predicate: str,
    object_val: str,
    conditions: list[str] | None = None,
    version_num: int = 1,
    doc_id: uuid.UUID | None = None,
    authority_level: int = 75,
    overall_trust: float = 0.95,
) -> Claim:
    cid = uuid.uuid4()
    common_doc_id = doc_id or uuid.uuid4()
    
    doc_ver = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=common_doc_id,
        version_number=version_num,
        document=SimpleNamespace(
            id=common_doc_id,
            source=SimpleNamespace(authority_level=authority_level),
        ),
    )
    
    trust_scores = [SimpleNamespace(overall_score=overall_trust)]
    validity_records = [SimpleNamespace(is_current=True, valid_until=None)]
    
    claim = SimpleNamespace(
        id=cid,
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        document_version_id=doc_ver.id,
        claim_text=claim_text,
        subject=subject,
        predicate=predicate,
        object=object_val,
        conditions=conditions or [],
        status=ClaimStatus.VERIFIED,
        document_version=doc_ver,
        trust_scores=trust_scores,
        validity_records=validity_records,
        evidence=[],
        authority_level=authority_level,
        claim_type="policy_rule",
    )
    return claim


# =========================================================================
# Invariant Test 1: Notice Period Matrix Complementarity (The 5 False-Positive Pairs)
# =========================================================================

@pytest.mark.parametrize(
    "grade_label,probation_days,confirmed_days",
    [
        ("Grade A (A1 & A2) (CXO)", "15 days", "90 Days"),
        ("Grade B (B1 & B2) (Senior Management)", "15 days", "90 Days"),
        ("Grade C (C1, C2 & C3) (Middle Management)", "15 days", "60 Days"),
        ("Grade D (D1, D2 & D3) (Junior Management)", "15 days", "30 Days"),
        ("Grade E (E1, E2 & E3) (Fellow)", "15 days", "30 Days"),
    ]
)
def test_notice_period_matrix_probation_vs_confirmed_are_complementary(
    grade_label: str, probation_days: str, confirmed_days: str
):
    """
    INVARIANT 1:
    A probationary notice rule and a confirmed notice rule for the same grade
    govern mutually exclusive employment phases. They must NOT be comparable
    for contradiction and must be classified as COMPLEMENTARY_CONDITIONAL_RULES.
    """
    claim_probation = _create_mock_claim(
        claim_text=f"Employees in {grade_label} have a notice period of {probation_days} during probation.",
        subject=f"Employees in {grade_label}",
        predicate="has_probationary_notice_duration",
        object_val=probation_days,
        conditions=["Probationary status"],
    )
    
    claim_confirmed = _create_mock_claim(
        claim_text=f"Employees in {grade_label} have a maximum notice period of {confirmed_days} upon confirmation.",
        subject=f"Employees in {grade_label}",
        predicate="has_confirmed_notice_duration",
        object_val=confirmed_days,
        conditions=["Confirmed status"],
    )

    outcome = CompatibilityGate.evaluate_compatibility(claim_probation, claim_confirmed)

    # Must NOT compete for the same decision key
    assert outcome.is_comparable is False
    assert outcome.relationship in ("COMPLEMENTARY_CONDITIONAL_RULES", "NON_OVERLAPPING_CONDITIONAL_SCOPE")
    assert "NON_OVERLAPPING" in outcome.reason or "ORTHOGONAL" in outcome.reason or "COMPLEMENTARY" in outcome.reason


# =========================================================================
# Invariant Test 2: True Numeric Contradiction Detection
# =========================================================================

def test_true_numeric_conflict_detected_when_keys_compete():
    """
    INVARIANT 2:
    When two claims have identical subjects, identical predicates, and overlapping
    conditions (e.g. Grade A confirmed is 90 days vs Grade A confirmed is 60 days)
    in the same document version, the gate must identify that keys COMPETE,
    leading to a genuine conflict detection.
    """
    claim_1 = _create_mock_claim(
        claim_text="Employees in Grade A (A1 & A2) (CXO) have a maximum notice period of 90 Days upon confirmation.",
        subject="Employees in Grade A (A1 & A2) (CXO)",
        predicate="has_confirmed_notice_duration",
        object_val="90 Days",
        conditions=["Confirmed status"],
    )
    
    claim_2 = _create_mock_claim(
        claim_text="Employees in Grade A (A1 & A2) (CXO) have a maximum notice period of 60 Days upon confirmation.",
        subject="Employees in Grade A (A1 & A2) (CXO)",
        predicate="has_confirmed_notice_duration",
        object_val="60 Days",
        conditions=["Confirmed status"],
    )

    outcome = CompatibilityGate.evaluate_compatibility(claim_1, claim_2)

    # Decision keys DO compete
    assert outcome.is_comparable is True
    assert outcome.reason == "COMPETING_DECISION_KEYS"
    
    # Values are incompatible
    is_conflict, conflict_type = CompatibilityGate.evaluate_value_conflict(claim_1, claim_2)
    assert is_conflict is True
    assert conflict_type in ("INCOMPATIBLE_NUMERIC_VALUE", "numerical_discrepancy")


# =========================================================================
# Invariant Test 3: Version Supersession (Not a Conflict)
# =========================================================================

def test_version_supersession_marks_outdated_not_conflicted():
    """
    INVARIANT 3:
    When Policy v2 changes Grade A confirmed notice to 60 days (previously 90 days in v1),
    PrecedenceEngine must deterministically resolve it as TEMPORAL_VERSION_PRECEDENCE,
    marking the v1 claim OUTDATED/SUPERSEDED rather than flagging both as CONFLICTED.
    """
    common_doc_id = uuid.uuid4()
    
    claim_v1 = _create_mock_claim(
        claim_text="Employees in Grade A (A1 & A2) (CXO) have a maximum notice period of 90 Days upon confirmation.",
        subject="Employees in Grade A (A1 & A2) (CXO)",
        predicate="has_confirmed_notice_duration",
        object_val="90 Days",
        conditions=["Confirmed status"],
        version_num=1,
        doc_id=common_doc_id,
    )
    
    claim_v2 = _create_mock_claim(
        claim_text="Employees in Grade A (A1 & A2) (CXO) have a maximum notice period of 60 Days upon confirmation.",
        subject="Employees in Grade A (A1 & A2) (CXO)",
        predicate="has_confirmed_notice_duration",
        object_val="60 Days",
        conditions=["Confirmed status"],
        version_num=2,
        doc_id=common_doc_id,
    )

    # 1. Compatibility Gate recognises competing keys
    outcome = CompatibilityGate.evaluate_compatibility(claim_v1, claim_v2)
    assert outcome.is_comparable is True

    # 2. Precedence Engine must auto-resolve without requiring human review
    precedence = PrecedenceEngine.evaluate_precedence(claim_v1, claim_v2)
    assert precedence.is_auto_resolved is True
    assert precedence.precedence_rule == "TEMPORAL_VERSION_PRECEDENCE"
    assert precedence.winner_claim_id == claim_v2.id
    assert precedence.loser_claim_id == claim_v1.id


# =========================================================================
# Invariant Test 4: Orthogonal Predicates on Same Entity
# =========================================================================

def test_orthogonal_predicates_on_same_subject_do_not_conflict():
    """
    INVARIANT 4:
    Claims governing the same entity (e.g., 'Employees') but operating on
    completely orthogonal predicates (e.g., 'return' property vs 'request_leave')
    must be immediately identified as non-comparable.
    """
    claim_asset = _create_mock_claim(
        claim_text="Employees must return all Wingify property upon offboarding.",
        subject="Employees",
        predicate="return",
        object_val="all Wingify property",
        conditions=["Upon offboarding"],
    )
    
    claim_leave = _create_mock_claim(
        claim_text="Employees may request leave during notice period only as an exception.",
        subject="Employees",
        predicate="request_leave_during_notice_period",
        object_val="leave during notice period",
        conditions=["Prior written approval"],
    )

    outcome = CompatibilityGate.evaluate_compatibility(claim_asset, claim_leave)
    assert outcome.is_comparable is False
    assert outcome.reason in ("ORTHOGONAL_PREDICATES", "DISJOINT_APPLICABILITY_SCOPE")
