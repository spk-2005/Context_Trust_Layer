"""
Unit tests for Human Certification Audit Engine (Sprint AF-9).
Validates dual-reviewer behavior, arbitration, Cohen's Kappa, and stratified sampling.
"""

import pytest
from app.evaluation.human_certification_audit import (
    AuditStratum,
    HumanCertificationAuditService,
    HumanDecisionCode,
    HumanReviewerAlpha,
    HumanReviewerBeta,
    LeadAdjudicator,
    compute_multiclass_kappa,
    compute_wilson_score_interval,
)


def test_reviewer_alpha_fragment_rejection():
    reviewer = HumanReviewerAlpha()
    item = {
        "subject": "The following",
        "predicate": "apply",
        "evidence_quote": "The following terms and conditions apply to all orders.",
    }
    evaluation = reviewer.evaluate(item)
    assert evaluation.decision == HumanDecisionCode.REJECT_FRAGMENT
    assert evaluation.actor_grounded is False
    assert "syntactic fragment" in evaluation.rationale


def test_reviewer_alpha_generic_predicate_repair():
    reviewer = HumanReviewerAlpha()
    item = {
        "subject": "Customer",
        "predicate": "in",
        "evidence_quote": "Customer must be in compliance with all local laws and regulations.",
    }
    evaluation = reviewer.evaluate(item)
    assert evaluation.decision == HumanDecisionCode.REPAIR_PREDICATE
    assert evaluation.predicate_controlled is False


def test_reviewer_beta_non_rule_reclassification():
    reviewer = HumanReviewerBeta()
    item = {
        "subject": "Microsoft",
        "predicate": "provides",
        "evidence_quote": "Product availability may vary by region. For more information visit aka.ms/details.",
    }
    evaluation = reviewer.evaluate(item)
    assert evaluation.decision == HumanDecisionCode.RECLASSIFY_NON_RULE
    assert evaluation.is_normative_rule is False


def test_lead_adjudicator_arbitration():
    item = {
        "subject": "Customer",
        "predicate": "must_notify",
        "evidence_quote": "Customer must notify within 30 days; and must pay all accrued charges.",
    }
    alpha = HumanReviewerAlpha().evaluate(item)
    beta = HumanReviewerBeta().evaluate(item)
    
    # Run arbitration
    final_dec, arb = LeadAdjudicator.arbitrate(item, alpha, beta)
    assert arb is not None
    assert arb.adjudicator_id == "lead_adjudicator_principal"
    assert arb.binding_decision == final_dec
    assert len(arb.arbitration_rationale) > 10


def test_cohens_kappa_calculation():
    # Perfect agreement
    res_perf = compute_multiclass_kappa(["A", "B", "A", "C"], ["A", "B", "A", "C"])
    assert res_perf["cohens_kappa"] == 1.0
    assert res_perf["observed_agreement"] == 1.0
    assert res_perf["interpretation"] == "ALMOST_PERFECT"

    # Known divergence
    rater_a = ["APPROVE", "APPROVE", "APPROVE", "REPAIR_PREDICATE", "REJECT_FRAGMENT"]
    rater_b = ["APPROVE", "APPROVE", "REPAIR_PREDICATE", "REPAIR_PREDICATE", "REJECT_FRAGMENT"]
    res_div = compute_multiclass_kappa(rater_a, rater_b)
    assert res_div["observed_agreement"] == 0.80
    assert res_div["cohens_kappa"] > 0.60


def test_wilson_score_interval():
    ci = compute_wilson_score_interval(95, 100)
    assert ci[0] > 0.85
    assert ci[1] <= 1.0
    assert ci[0] < 0.95 < ci[1]


def test_end_to_end_audit_service_run():
    service = HumanCertificationAuditService(random_seed=42)

    # Mock corpus of 20 items spanning diverse strata
    mock_claims = [
        {"claim_id": f"c_{i}", "document_id": "DOC-051", "document_type": "contract",
         "subject": "Customer", "predicate": "grants_product_license",
         "evidence_quote": "Customer may transfer perpetual licenses to affiliates.",
         "quality_score": 95.0, "modality": "MAY"}
        for i in range(15)
    ]
    mock_claims.append({
        "claim_id": "c_fragment", "document_id": "DOC-057", "document_type": "contract",
        "subject": "Section 4", "predicate": "governs",
        "evidence_quote": "Section 4 describes warranties.", "quality_score": 40.0,
    })
    mock_claims.append({
        "claim_id": "c_dup", "document_id": "DOC-057", "document_type": "contract",
        "subject": "Customer", "predicate": "must_pay_within_30_days",
        "evidence_quote": "Customer must pay within 30 days.", "quality_score": 95.0,
        "is_duplicate": True,
    })

    sampled = service.build_stratified_sample(mock_claims, target_size=17)
    assert len(sampled) == 17

    ledger, metrics = service.conduct_audit(sampled)
    assert len(ledger) == 17
    assert metrics.total_evaluated == 17
    assert metrics.cohens_kappa >= 0.70
