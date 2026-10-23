"""
Unit tests for Human Certification Workspace & Ingestion Pipeline (Sprint AF-14).
Validates:
1. Stripping of confidence and prior dispositions to produce blinded review queues.
2. Ingestion of dual human review submissions.
3. Divergence arbitration and Cohen's Kappa calculation.
"""

from pathlib import Path
import pytest

from app.evaluation.human_certification_workspace import (
    HumanCertificationWorkspace,
    HumanReviewSubmission,
    BlindedClaimItem,
)
from app.evaluation.human_certification_audit import HumanDecisionCode as DecisionCode


def test_create_blinded_queues_strips_pipeline_hints():
    mock_claims = [
        {
            "claim_id": f"CLM-{i:03d}",
            "document_id": "DOC-057",
            "status": "CANONICAL",
            "confidence": 0.99,
            "quality_score": 98.5,
            "subject": {"canonical_entity": "Customer"},
            "predicate": {"normalized_action": "must_pay"},
            "object": {"normalized_object": "invoiced fees"},
            "modality": "MUST",
            "evidence": {
                "verbatim_quote": "Customer must pay all invoiced fees.",
                "clause_text": "Customer must pay all invoiced fees within 30 days.",
                "page": 2,
            },
            "gates": {"span_exists": True, "clause_entails_claim": True},
        }
        for i in range(20)
    ]

    q_alpha, q_beta = HumanCertificationWorkspace.create_blinded_queues(mock_claims, sample_size=10)

    assert len(q_alpha) == 10
    assert len(q_beta) == 10

    for item in q_alpha:
        item_dict = item.model_dump()
        # Verify no confidence, score, or prior pipeline status was leaked
        assert "confidence" not in item_dict
        assert "quality_score" not in item_dict
        assert "status" not in item_dict
        assert "gates" not in item_dict

        # Verify essential audit fields are present
        assert item.verbatim_quote != ""
        assert item.enclosing_clause_text != ""
        assert item.guidelines_reference == "docs/annotation_guidelines_v3.md"


def test_process_human_reviews_consensus_and_divergence():
    alpha_submissions = [
        HumanReviewSubmission(
            claim_id="CLM-001",
            reviewer_id="HUMAN_COUNSEL_ALPHA",
            timestamp="2026-10-21T09:00:00Z",
            decision_code=DecisionCode.APPROVE,
            rationale="Exact atomic contractual obligation.",
        ),
        HumanReviewSubmission(
            claim_id="CLM-002",
            reviewer_id="HUMAN_COUNSEL_ALPHA",
            timestamp="2026-10-21T09:01:00Z",
            decision_code=DecisionCode.REPAIR_PREDICATE,
            rationale="Action predicate should normalize to may_transfer_license.",
        ),
    ]

    beta_submissions = [
        HumanReviewSubmission(
            claim_id="CLM-001",
            reviewer_id="HUMAN_COMPLIANCE_BETA",
            timestamp="2026-10-21T09:05:00Z",
            decision_code=DecisionCode.APPROVE,
            rationale="Agreed with approval.",
        ),
        HumanReviewSubmission(
            claim_id="CLM-002",
            reviewer_id="HUMAN_COMPLIANCE_BETA",
            timestamp="2026-10-21T09:06:00Z",
            decision_code=DecisionCode.SPLIT_COMPOUND,
            rationale="Suggest splitting into separate affiliate rights.",
        ),
    ]

    records, metrics = HumanCertificationWorkspace.process_human_reviews_and_adjudicate(
        alpha_submissions, beta_submissions, lead_adjudicator_id="LEAD_ADJUDICATOR_HUMAN"
    )

    assert len(records) == 2
    assert metrics["total_evaluated"] == 2
    assert metrics["total_agreed"] == 1
    assert metrics["divergence_count"] == 1

    # Record 1 had consensus
    assert records[0].consensus_reached is True
    assert records[0].lead_adjudicator_id is None
    assert records[0].final_decision == DecisionCode.APPROVE

    # Record 2 had divergence arbitrated by Lead Adjudicator
    assert records[1].consensus_reached is False
    assert records[1].lead_adjudicator_id == "LEAD_ADJUDICATOR_HUMAN"
    assert "Arbitrated divergence" in records[1].adjudication_rationale
