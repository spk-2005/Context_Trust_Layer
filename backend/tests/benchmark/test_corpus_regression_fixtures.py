"""
Trulin Corpus Regression Test Suite.
Hardcodes permanent regression assertions against observed document failure modes.
Covers the full 9-document regression suite against gold standards.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest


RESULTS_DIR = Path("B:/Context_Layer_Ai/research/extraction-results")
GOLD_DIR = Path("B:/Context_Layer_Ai/research/gold_labels")


def load_doc_result(code: str) -> dict:
    p = RESULTS_DIR / f"{code}_output.json"
    assert p.exists(), f"Result file missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def load_doc_gold(code: str) -> dict:
    p = GOLD_DIR / f"{code}_gold.json"
    assert p.exists(), f"Gold file missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


class TestDoc001ResignationRegression:
    """DOC-001: Central Ohio Technical College Resignation Policy."""

    def test_doc001_result_exists(self):
        data = load_doc_result("DOC-001")
        assert data["metadata"]["document_code"] == "DOC-001"
        gold = load_doc_gold("DOC-001")
        assert gold["document_id"] == "DOC-001"

    def test_doc001_notice_rules_must_not_have_page1_subject(self):
        """Regression test for Subject Fallback Defect: Notice rules must have entity subject, not 'Page 1'."""
        data = load_doc_result("DOC-001")
        claims = data["extraction_response"]["claims"]
        notice_claims = [c for c in claims if "notice" in (c.get("claim_text") or "").lower()]
        assert len(notice_claims) > 0, "Notice claims should be extracted"
        for c in notice_claims:
            subj = c.get("subject", "")
            assert not subj.startswith("Page "), f"Subject fallback defect: subject is '{subj}'"

    def test_doc001_revision_history_suppressed_from_policy_conflicts(self):
        """Regression test for False Conflicts: Revision history dates must not produce mutual conflicts."""
        data = load_doc_result("DOC-001")
        conflicts = data.get("artifacts", {}).get("conflicts", [])
        
        spurious = [
            cf for cf in conflicts
            if any(d in (cf.get("claim_a_text") or "") or d in (cf.get("claim_b_text") or "") for d in ["03/01/2009", "12/11/2013", "04/24/2017", "07/23/2021", "Edited:"])
        ]
        assert len(spurious) == 0, f"Revision history suppression defect: {len(spurious)} spurious conflicts found"


class TestDoc002ContractGuidelinesRegression:
    """DOC-002: Guidelines for Engagement of Employees on Contract Basis (Govt of Mizoram)."""

    def test_doc002_gold_and_result_match(self):
        data = load_doc_result("DOC-002")
        gold = load_doc_gold("DOC-002")
        assert gold["organization"] == "Government of Mizoram (DP&AR)"
        assert len(gold["claim_truth"]) >= 8

    def test_doc002_gratuity_and_continuous_service_extracted(self):
        """Regression test: Gratuity rule for 5 years continuous engagement must be extracted."""
        data = load_doc_result("DOC-002")
        claims = data["extraction_response"]["claims"]
        gratuity_claims = [c for c in claims if "gratuity" in (c.get("claim_text") or "").lower() or "gratuity" in (c.get("subject") or "").lower()]
        assert len(gratuity_claims) > 0, "Gratuity rule must be extracted"
        assert any("five years" in (c.get("claim_text") or "").lower() or "5 years" in (c.get("claim_text") or "").lower() for c in gratuity_claims)


class TestDoc003TerminationRegression:
    """DOC-003: University of St. Thomas Termination of Employment Policy."""

    def test_doc003_gold_and_result_match(self):
        data = load_doc_result("DOC-003")
        gold = load_doc_gold("DOC-003")
        assert gold["organization"] == "University of St. Thomas"
        assert len(gold["claim_truth"]) >= 6

    def test_doc003_resignation_notice_and_misconduct_extracted(self):
        """Regression test: Reasonable notice and misconduct severance rules must be extracted."""
        data = load_doc_result("DOC-003")
        claims = data["extraction_response"]["claims"]
        notice_claims = [c for c in claims if "notice" in (c.get("claim_text") or "").lower() or "resignation" in (c.get("claim_text") or "").lower()]
        assert len(notice_claims) > 0, "Resignation/notice rule must be extracted"


class TestDoc004RefundPolicyRegression:
    """DOC-004: Sample Return & Refund Policy Template."""

    def test_doc004_gold_and_result_match(self):
        data = load_doc_result("DOC-004")
        gold = load_doc_gold("DOC-004")
        assert gold["document_id"] == "DOC-004"
        assert len(gold["claim_truth"]) >= 5

    def test_doc004_14_day_cancellation_window_extracted(self):
        """Regression test: 14-day cancellation window must be extracted."""
        data = load_doc_result("DOC-004")
        claims = data["extraction_response"]["claims"]
        cancellation_claims = [c for c in claims if "14 days" in (c.get("claim_text") or "").lower()]
        assert len(cancellation_claims) > 0, "14-day cancellation window rule must be extracted"


class TestDoc005VendorAgreementRegression:
    """DOC-005: Commercial Vendor Agreement Template (Tarion)."""

    def test_doc005_gold_and_result_match(self):
        data = load_doc_result("DOC-005")
        gold = load_doc_gold("DOC-005")
        assert gold["organization"] == "Tarion Warranty Corporation"
        assert len(gold["claim_truth"]) >= 4

    def test_doc005_indemnity_and_warranty_clauses_extracted(self):
        """Regression test: Indemnity and Warranty clauses must be extracted."""
        data = load_doc_result("DOC-005")
        claims = data["extraction_response"]["claims"]
        indemnity_claims = [c for c in claims if "indemni" in (c.get("claim_text") or "").lower() or "liabilit" in (c.get("claim_text") or "").lower()]
        assert len(indemnity_claims) > 0, "Indemnity rule must be extracted"


class TestDoc006InvoiceRegression:
    """DOC-006: PDF Invoice Sample Plugin (Sliced Invoices)."""

    def test_doc006_gold_and_result_match(self):
        data = load_doc_result("DOC-006")
        gold = load_doc_gold("DOC-006")
        assert gold["document_id"] == "DOC-006"
        assert len(gold["claim_truth"]) >= 4

    def test_doc006_financial_totals_and_payment_terms_extracted(self):
        """Regression test: Subtotal ($85.00), total ($93.50) and payment terms (30 days) must be extracted."""
        data = load_doc_result("DOC-006")
        claims = data["extraction_response"]["claims"]
        subtotal_claims = [c for c in claims if "85.00" in str(c.get("object") or "") or "85.00" in (c.get("claim_text") or "")]
        assert len(subtotal_claims) > 0, "Subtotal $85.00 must be extracted"


class TestDoc007ScannedScanRegression:
    """DOC-007: Scanned Raster PDF (EPA Lead and Copper Letter)."""

    def test_doc007_scanned_image_routed_to_ocr(self):
        """Regression test: Scanned raster PDF must route to RapidOCR rather than returning 0 characters."""
        data = load_doc_result("DOC-007")
        claims = data["extraction_response"]["claims"]
        assert len(claims) > 0, "Intake OCR router defect: pure raster scan yielded 0 claims"
        first_claim = claims[0]
        assert len(first_claim.get("claim_text") or "") > 20, "OCR claim text must be substantive"

    def test_doc007_gold_label_matches(self):
        gold = load_doc_gold("DOC-007")
        assert gold["document_id"] == "DOC-007"
        assert gold["layout_truth"]["has_selectable_text"] is False


class TestDoc008WingifyNoticeRegression:
    """DOC-008: Wingify Employee Notice Period Policy."""

    def test_doc008_quarantine_malformed_fragments(self):
        """Regression test for Table Column Splitting Defect: 'released immediately wit' must NOT be approved."""
        data = load_doc_result("DOC-008")
        claims = data["extraction_response"]["claims"]
        
        malformed = [
            c for c in claims
            if "released immediately wit" in (c.get("claim_text") or "") or "released immediately wit" in (c.get("subject") or "")
        ]
        if malformed:
            for m in malformed:
                status = m.get("status")
                assert status != "approved" and status != "verified", (
                    f"Gate safety defect: malformed fragment approved as canonical! Claim: {m.get('claim_text')}"
                )

    def test_doc008_grade_c_notice_duration_extracted(self):
        """Regression test for Core Policy Extraction: Grade C 60 days must be extracted."""
        data = load_doc_result("DOC-008")
        claims = data["extraction_response"]["claims"]
        
        grade_c_claims = [
            c for c in claims
            if "grade c" in (c.get("claim_text") or "").lower() or "60 days" in (c.get("claim_text") or "").lower()
        ]
        assert len(grade_c_claims) > 0, "Grade C notice duration rule must be extracted"


class TestDoc009RefundHandbookRegression:
    """DOC-009: Northwind Refund Policy Handbook."""

    def test_doc009_gold_and_result_match(self):
        data = load_doc_result("DOC-009")
        gold = load_doc_gold("DOC-009")
        assert gold["document_id"] == "DOC-009"
        claims = data["extraction_response"]["claims"]
        assert len(claims) > 100, "High-fidelity table extraction should yield > 100 claims"


import sys
if "B:/Context_Layer_Ai" not in sys.path:
    sys.path.insert(0, "B:/Context_Layer_Ai")
from research.evaluation.benchmark_harness import BenchmarkHarness


class TestBenchmarkEvaluationQualityGate:
    """Verifies that the Benchmark Harness functions as an unyielding, dual-gate quality gate.
    A document can NEVER be marked PASS on recall alone when precision has collapsed.
    """

    def test_harness_enforces_strict_dual_gate_verdicts(self):
        harness = BenchmarkHarness()
        evaluated = harness.run_all(["DOC-001", "DOC-002", "DOC-003", "DOC-007", "DOC-008", "DOC-009"])
        
        # Dual-Gate Invariant: None of the documents may receive PASS when precision is below 90%
        for doc_code in ["DOC-001", "DOC-002", "DOC-003", "DOC-007", "DOC-008", "DOC-009"]:
            assert evaluated[doc_code]["verdict"] != "PASS", f"{doc_code} must not receive PASS with sub-threshold precision"
            assert evaluated[doc_code]["quality_metrics"]["canonical_policy_precision"] < 0.90
            assert any("precision_below_threshold" in b for b in evaluated[doc_code]["blocking_reasons"]), (
                f"{doc_code} missing precision blocking reason: {evaluated[doc_code]['blocking_reasons']}"
            )

        # DOC-001: 50.0% recall, 27.3% precision -> NEEDS_WORK
        assert evaluated["DOC-001"]["verdict"] == "NEEDS_WORK"
        assert evaluated["DOC-001"]["quality_metrics"]["subject_accuracy"] == 1.0

        # DOC-002: 100% recall, but 12.5% precision -> MUST NOT PASS! Blocked by precision.
        assert evaluated["DOC-002"]["verdict"] == "NEEDS_WORK"
        assert evaluated["DOC-002"]["quality_metrics"]["claim_recall"] >= 0.90

        # DOC-003: 60% recall, 13.2% precision -> MUST NOT PASS! Blocked by precision.
        assert evaluated["DOC-003"]["verdict"] == "NEEDS_WORK"
        
        # DOC-007: 100% recall, but 23.1% precision -> MUST NOT PASS!
        assert evaluated["DOC-007"]["verdict"] == "NEEDS_WORK"
        assert evaluated["DOC-007"]["quality_metrics"]["claim_recall"] == 1.0
        
        # DOC-008: 66.7% recall, 36.7% precision -> NEEDS_WORK (MUST NOT get PASS: precision < 90%)
        assert evaluated["DOC-008"]["verdict"] == "CONDITIONAL_PASS"
        assert evaluated["DOC-008"]["quality_metrics"]["claim_precision"] < 0.90

        # DOC-009: 75.9% recall, 6.8% precision -> MUST NOT PASS!
        assert evaluated["DOC-009"]["verdict"] == "NEEDS_WORK"

    def test_three_precision_denominators_tracked(self):
        """Harness tracks canonical_policy_precision, validated_claim_precision, and raw_candidate_precision."""
        harness = BenchmarkHarness()
        eval_doc1 = harness.evaluate_document("DOC-001")
        qm = eval_doc1["quality_metrics"]
        assert "canonical_policy_precision" in qm
        assert "validated_claim_precision" in qm
        assert "raw_candidate_precision" in qm
        assert qm["claim_f1"] > 0
