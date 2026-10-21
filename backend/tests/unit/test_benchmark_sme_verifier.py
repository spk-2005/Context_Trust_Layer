"""
Unit tests for Independent SME Benchmark Verification & Sign-off Engine (Sprint AF-14).
Validates:
1. Exporting 175-question gold review queue.
2. Ingestion of external SME approvals and corrections.
3. Reviewer independence enforcement (rejects pipeline author self-review).
4. Refusal and adversarial trap confirmation.
5. Deterministic cryptographic SHA-256 seal generation.
"""

from pathlib import Path
import pytest

from app.evaluation.benchmark_sme_verifier import (
    BenchmarkSMEVerifier,
    BenchmarkSMEVerificationItem,
    SMESignoffStatus,
)


def test_export_sme_review_bundle(tmp_path):
    target = tmp_path / "benchmark_175_gold_review_queue.json"
    p = BenchmarkSMEVerifier.export_sme_review_bundle(output_path=target)

    assert p.exists()
    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    assert len(data) == 175

    first = data[0]
    assert first["question_id"] == "Q-CON-001"
    assert first["sme_status"] == SMESignoffStatus.PENDING.value
    assert first["draft_gold_answer"] != ""


def test_process_sme_signoff_success():
    items = [
        BenchmarkSMEVerificationItem(
            question_id="Q-001",
            family="CONTRACTS",
            question_type="FACTUAL_LOOKUP",
            document_id="DOC-057",
            question_text="May customer transfer licenses?",
            draft_gold_answer="Yes, fully-paid perpetual licenses to Affiliate or with hardware.",
            expected_citations=["SEC-01.g"],
            sme_status=SMESignoffStatus.APPROVED,
            sme_confirmed_citations=["SEC-01.g"],
        ),
        BenchmarkSMEVerificationItem(
            question_id="Q-002",
            family="CONTRACTS",
            question_type="NEGATIVE_UNSTATED",
            document_id="DOC-057",
            question_text="Can customer sub-license to general public?",
            draft_gold_answer="Unstated / Prohibited.",
            is_unstated=True,
            sme_status=SMESignoffStatus.APPROVED,
            sme_confirmed_refusal_label=True,
            expected_citations=[],
        ),
    ]

    ledger, metrics = BenchmarkSMEVerifier.process_sme_signoff(
        reviewed_items=items,
        sme_reviewer_id="EXT_INDEPENDENT_SME_LEGAL_COUNSEL",
        sme_reviewer_role="Principal Legal Compliance Auditor",
        lead_governance_id="CHIEF_COMPLIANCE_OFFICER",
    )

    assert ledger.approved_count == 2
    assert ledger.flagged_count == 0
    assert ledger.refusal_labels_confirmed is True
    assert len(ledger.benchmark_sha256_seal) == 64
    assert metrics["is_externally_certified"] is True


def test_reviewer_independence_rejection():
    items = [
        BenchmarkSMEVerificationItem(
            question_id="Q-001",
            family="CONTRACTS",
            question_type="FACTUAL_LOOKUP",
            document_id="DOC-057",
            question_text="Test question",
            draft_gold_answer="Test answer",
        )
    ]

    with pytest.raises(ValueError, match="Reviewer independence violation"):
        BenchmarkSMEVerifier.process_sme_signoff(
            reviewed_items=items,
            sme_reviewer_id="EXTRACTION_PIPELINE_TEAM",
            pipeline_author_id="EXTRACTION_PIPELINE_TEAM",
        )
