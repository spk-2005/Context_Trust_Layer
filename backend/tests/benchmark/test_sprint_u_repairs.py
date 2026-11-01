from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import hashlib
import json
import pytest

from research.evaluation.benchmark_harness import BenchmarkHarness
from app.extraction.subject_normalizer import SubjectNormalizer
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor

EVAL_DIR = ROOT_DIR / "research" / "evaluation"
HOLDOUT_DIR = ROOT_DIR / "research" / "holdout"


def test_invoice_subject_total_validity_barrier():
    """Verify invoice subject 'Total' is treated as a valid operative entity in financial documents."""
    harness = BenchmarkHarness()
    res = harness.evaluate_document("DOC-006")
    
    assert res["quality_metrics"]["subject_accuracy"] == 1.0, "DOC-006 subject accuracy must be 1.0"
    assert res["quality_metrics"]["malformed_fragment_rate"] == 0.0, "DOC-006 malformed rate must be 0.0"
    assert res["candidate_ledger"]["incorrect_predictions"] == 0, "No incorrect subject predictions permitted on DOC-006"
    assert res["metrics"]["full_match_recall"] == 1.0, "DOC-006 must achieve 100% full-match recall"


def test_payment_terms_not_mapped_to_return_windows():
    """Verify payment terms map to payment obligations, NEVER to return windows or shipping fees."""
    sent1 = "Payment is due within 30 days from date of invoice."
    pred1, obj1, mod1 = DomainRuleExtractor.normalize_predicate_and_modality(
        raw_pred="due", raw_pred_obj="within 30 days from date of invoice",
        clean_sentence=sent1, raw_modal="is", current_modality="MUST"
    )
    assert pred1 == "has_due_date_period", f"Expected has_due_date_period, got {pred1}"
    assert "return_window" not in pred1, "Payment terms must NEVER map to return_window"

    sent2 = "Late payment is subject to fees of 5% per month."
    pred2, obj2, mod2 = DomainRuleExtractor.normalize_predicate_and_modality(
        raw_pred="subject", raw_pred_obj="to fees of 5% per month",
        clean_sentence=sent2, raw_modal="is", current_modality="MAY"
    )
    assert pred2 == "may_apply_administration_fee", f"Expected may_apply_administration_fee, got {pred2}"
    assert "shipping" not in pred2, "Late fee must NEVER map to shipping fee"


def test_contract_covenant_subject_normalization():
    """Verify covenant subjects strip clause prefixes and resolve to operative actors."""
    raw1 = "3.9.3.6 The Warranty Information Sheet and Addendum templates"
    clean1 = SubjectNormalizer.clean_raw_subject(raw1)
    import re
    stripped1 = re.sub(r"^\d+(\.\d+)*\s*", "", clean1).strip()
    assert stripped1 == "The Warranty Information Sheet and Addendum templates"

    sub2, ok2 = SubjectNormalizer.normalize("3.6.3.2", context="The Vendor shall fulfill all obligations")
    assert ok2 is True
    assert sub2 == "Vendor"


def test_dual_review_inter_annotator_agreement_studies():
    """Verify DOC-002, DOC-007, and DOC-008 have certified Cohen's Kappa >= 0.85."""
    docs = [
        ("DOC-002", EVAL_DIR / "doc002_inter_annotator_agreement.json", 0.85),
        ("DOC-007", EVAL_DIR / "doc007_inter_annotator_agreement.json", 0.85),
        ("DOC-008", EVAL_DIR / "doc008_inter_annotator_agreement.json", 0.85),
    ]

    for doc_id, file_path, min_kappa in docs:
        assert file_path.exists(), f"Missing IAA file: {file_path}"
        data = json.loads(file_path.read_text(encoding="utf-8"))
        assert data["document_id"] == doc_id
        kappa = data["cohen_kappa"]
        assert kappa >= min_kappa, f"{doc_id} Cohen's Kappa {kappa} below required {min_kappa}"
        cert = data.get("conditional_pass_certification", {})
        assert cert.get("status") == "CONFIRMED", f"{doc_id} certification must be CONFIRMED"


def test_sealed_holdout_11_field_provenance_block():
    """Verify sealed holdout report contains the complete 11-field provenance block matching manifest SHA-256."""
    report_file = HOLDOUT_DIR / "holdout_evaluation_report.json"
    manifest_file = HOLDOUT_DIR / "holdout_manifest.json"

    assert report_file.exists()
    assert manifest_file.exists()

    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    prov = report_data.get("holdout_provenance")
    assert prov is not None, "Missing holdout_provenance block in holdout_evaluation_report.json"

    required_fields = [
        "manifest_path", "manifest_sha256", "sealed_at", "corpus_status",
        "total_documents", "total_gold_rules", "evaluation_mode",
        "synthetic_injections_detected", "leakage_audit_status",
        "holdout_integrity_barrier", "governance_standard"
    ]
    for field in required_fields:
        assert field in prov, f"Missing required provenance field: {field}"

    actual_manifest_sha = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    assert prov["manifest_sha256"] == actual_manifest_sha, (
        f"Manifest SHA-256 mismatch in holdout provenance: expected {actual_manifest_sha}, got {prov['manifest_sha256']}"
    )
    assert prov["corpus_status"] == "SEALED_AND_FROZEN"
    assert prov["total_documents"] == 15
    assert prov["total_gold_rules"] == 200
    assert prov["synthetic_injections_detected"] == 0


def test_authentic_baseline_invariants():
    """Verify authentic baseline recall metrics for DOC-005 (6.25 percent), DOC-006 (100 percent), and DOC-009 (19.23 percent) without malformations."""
    harness = BenchmarkHarness()

    # DOC-005 authentic baseline: 2/32 full matches = 6.25% recall
    res_005 = harness.evaluate_document("DOC-005")
    assert pytest.approx(res_005["metrics"]["full_match_recall"], 0.001) == 0.0625
    assert res_005["quality_metrics"]["malformed_fragment_rate"] == 0.0
    assert res_005["quality_metrics"]["evidence_span_traceability"] == 1.0
    assert res_005["verdict"] == "NEEDS_WORK"

    # DOC-006 domain-general invoice rule: 5/5 full matches = 100% recall
    res_006 = harness.evaluate_document("DOC-006")
    assert res_006["metrics"]["full_match_recall"] == 1.0
    assert res_006["quality_metrics"]["malformed_fragment_rate"] == 0.0
    assert res_006["quality_metrics"]["evidence_span_traceability"] == 1.0
    assert res_006["verdict"] == "PASS"

    # DOC-009 authentic baseline: 15/78 full matches = 19.23% recall
    res_009 = harness.evaluate_document("DOC-009")
    assert pytest.approx(res_009["metrics"]["full_match_recall"], 0.001) == 0.1923
    assert res_009["quality_metrics"]["malformed_fragment_rate"] == 0.0
    assert res_009["quality_metrics"]["evidence_span_traceability"] == 1.0
    assert res_009["verdict"] == "NEEDS_WORK"
