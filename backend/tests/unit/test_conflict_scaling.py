import uuid
import pytest
from app.conflict_engine.facet_sharder import FacetSharder
from app.conflict_engine.multi_agent_arbiter import MultiAgentArbiter
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict


def test_facet_sharder_classification():
    text_support = "Customer support is available via phone and live chat 24/7."
    text_refund = "Returns must be requested within 30 calendar days from delivery."
    text_warranty = "Tents and outdoor equipment are covered by a 2-year warranty against defects."

    assert FacetSharder.detect_facet(text_support) == "support_channels"
    assert FacetSharder.detect_facet(text_refund) == "return_window"
    assert FacetSharder.detect_facet(text_warranty) == "product_warranty"

    # Support and return window are orthogonal
    assert not FacetSharder.are_facets_compatible("support_channels", "return_window")
    # Same facet is compatible
    assert FacetSharder.are_facets_compatible("return_window", "return_window")


def test_multi_agent_arbiter_statutory_precedence():
    org_id = uuid.uuid4()
    doc_ver_id = uuid.uuid4()
    claim_a = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=doc_ver_id,
        claim_text="Standard return window is strictly 30 days with no exceptions allowed.",
        subject="Return Policy",
        predicate="specifies",
        object="30 days",
        claim_type="policy",
        extraction_method="rule_based",
        extraction_model="model_v1",
    )
    claim_b = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=doc_ver_id,
        claim_text="Statutory mandatory cooling-off period grants EU distance purchasers 14 days under consumer law.",
        subject="EU Statutory Rights",
        predicate="specifies",
        object="14 days",
        claim_type="policy",
        extraction_method="rule_based",
        extraction_model="model_v1",
    )
    conflict = ClaimConflict(
        id=uuid.uuid4(),
        claim_a_id=claim_a.id,
        claim_b_id=claim_b.id,
        conflict_type="policy_discrepancy",
        severity="medium",
    )

    verdict = MultiAgentArbiter.evaluate_arbitration(
        conflict=conflict,
        claim_a=claim_a,
        claim_b=claim_b,
        impact_score=35.0,  # Below critical threshold
    )

    assert verdict.is_auto_arbitrated is True
    assert verdict.winner_claim_id == claim_b.id
    assert "Statutory Compliance" in verdict.judge_verdict


def test_multi_agent_arbiter_critical_blast_escalation():
    org_id = uuid.uuid4()
    doc_ver_id = uuid.uuid4()
    claim_a = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=doc_ver_id,
        claim_text="Executive board approval required for refunds over $50,000.",
        subject="Executive Limits",
        predicate="requires",
        object="approval",
        claim_type="policy",
        extraction_method="rule_based",
        extraction_model="model_v1",
    )
    claim_b = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=doc_ver_id,
        claim_text="Department VP can sign off on refunds up to $100,000 without board approval.",
        subject="VP Limits",
        predicate="permits",
        object="sign off",
        claim_type="policy",
        extraction_method="rule_based",
        extraction_model="model_v1",
    )
    conflict = ClaimConflict(
        id=uuid.uuid4(),
        claim_a_id=claim_a.id,
        claim_b_id=claim_b.id,
        conflict_type="numerical_discrepancy",
        severity="critical",
    )

    # High blast radius (>= 60) must escalate to human auditor
    verdict = MultiAgentArbiter.evaluate_arbitration(
        conflict=conflict,
        claim_a=claim_a,
        claim_b=claim_b,
        impact_score=85.0,
    )

    assert verdict.is_auto_arbitrated is False
    assert verdict.is_critical_escalation is True
    assert "Escalated to Human Auditor" in verdict.rationale
