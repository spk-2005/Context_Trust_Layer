"""
Anti-Tamper & Governance Invariant Tests (Sprint W)
==================================================
Milestone: Sprint W: Holdout Refresh, Governance Coherence & Initial Recall Restoration
Governance Standard: Antigravity Evaluation Contract v1.0.0

Tests:
  1. AST Invariance: Zero occurrences of gold_subjects or gold-conditioned evaluation logic in benchmark_harness.py
  2. Extraction Artifact Integrity: DOC-005 (129 claims) and DOC-009 (250 claims) match git HEAD without synthetic markers
  3. Adjudication Decoupling Invariant: Unreviewed pools report adjudicated_precision = None, never 1.0 (100%)
  4. Pilot Decision Invariant: Exactly DOC-002, DOC-006, DOC-007, and DOC-008 are CONDITIONAL_GO (all backed by certified dual IAA)
  5. Sealed Holdout Provenance Invariant: 11-field cryptographic block + staleness audit fields validation
  6. Lifecycle Provenance Barrier Invariant: LifecycleProvenanceGuard all 8 stages pass
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, List
import pytest

ROOT_DIR = Path("B:/Context_Layer_Ai")
EVAL_DIR = ROOT_DIR / "research" / "evaluation"
HOLDOUT_DIR = ROOT_DIR / "research" / "holdout"
RESULTS_DIR = ROOT_DIR / "research" / "extraction-results"

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from benchmark_harness import BenchmarkHarness
from lifecycle_provenance_guard import LifecycleProvenanceGuard, get_claims_list


class TestAntiTamperInvariants:
    """Rigorous anti-tamper, zero-gold-leakage, and governance invariant test suite."""

    def test_ast_zero_gold_leakage_in_harness(self):
        """Verify benchmark_harness.py contains zero occurrences of gold_subjects or gold-conditioned entity filtering."""
        harness_path = EVAL_DIR / "benchmark_harness.py"
        assert harness_path.exists(), f"Missing {harness_path}"

        tree = ast.parse(harness_path.read_text(encoding="utf-8"))

        forbidden_names = {"gold_subjects"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in forbidden_names, (
                    f"Forbidden gold-leakage identifier '{node.id}' found at line {node.lineno}"
                )
            elif isinstance(node, ast.Attribute):
                assert node.attr not in forbidden_names, (
                    f"Forbidden gold-leakage attribute '{node.attr}' found at line {node.lineno}"
                )

        code_text = harness_path.read_text(encoding="utf-8")
        assert 'is_invoice = (canonical_doc_type == "invoice")' in code_text
        assert 'sub.lower() in ("total", "subtotal", "tax") and not is_invoice' in code_text

    def test_extraction_artifact_head_integrity(self):
        """Verify DOC-005 and DOC-009 extraction outputs match git HEAD claim counts without synthetic markers."""
        doc005_path = RESULTS_DIR / "DOC-005_output.json"
        doc009_path = RESULTS_DIR / "DOC-009_output.json"
        audit_path = EVAL_DIR / "artifact_diff_audit.json"

        assert doc005_path.exists()
        assert doc009_path.exists()
        assert audit_path.exists()

        data005 = json.loads(doc005_path.read_text(encoding="utf-8"))
        data009 = json.loads(doc009_path.read_text(encoding="utf-8"))
        audit_data = json.loads(audit_path.read_text(encoding="utf-8"))

        claims_005 = get_claims_list(data005)
        claims_009 = get_claims_list(data009)

        assert len(claims_005) == 129, f"DOC-005 must have 129 claims, got {len(claims_005)}"
        assert len(claims_009) == 250, f"DOC-009 must have 250 claims, got {len(claims_009)}"

        for c in claims_005:
            assert "synthetic" not in str(c).lower()
        for c in claims_009:
            assert "synthetic" not in str(c).lower()

        assert audit_data["executive_verdict"] == "SYNTHETIC_INJECTIONS_PURGED_AND_REVERTED"

    def test_adjudication_precision_decoupling_invariant(self):
        """Verify unreviewed documents strictly report adjudicated_precision = None, never 1.0."""
        harness = BenchmarkHarness(results_dir=RESULTS_DIR)

        # Unreviewed documents
        for code in ["DOC-001", "DOC-003", "DOC-004", "DOC-005", "DOC-009"]:
            res = harness.evaluate_document(code)
            adj_p = res["metrics"]["adjudicated_precision"]
            assert adj_p is None, f"{code} unreviewed candidates must report adjudicated_precision=None, got {adj_p}"
            assert res["metrics"]["adjudicated_claim_count"] == 0

        # Reviewed documents: DOC-002, DOC-006, DOC-007, DOC-008
        for code in ["DOC-002", "DOC-006", "DOC-007", "DOC-008"]:
            res = harness.evaluate_document(code)
            adj_p = res["metrics"]["adjudicated_precision"]
            assert isinstance(adj_p, float), f"{code} reviewed candidates must report float precision, got {adj_p}"
            assert res["metrics"]["adjudicated_claim_count"] > 0
            assert adj_p >= 0.90, f"{code} adjudicated precision {adj_p} below 90%"

    def test_pilot_decision_consistency_and_iaa_alignment(self):
        """Verify only DOC-002, DOC-006, DOC-007, and DOC-008 are CONDITIONAL_GO (all backed by certified dual IAA)."""
        matrix_path = EVAL_DIR / "all_documents_verdict_matrix.json"
        if not matrix_path.exists():
            pytest.skip("all_documents_verdict_matrix.json not yet regenerated")

        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))

        expected_pilot_decisions = {
            "DOC-001": "NO-GO",
            "DOC-002": "CONDITIONAL_GO",
            "DOC-003": "NO-GO",
            "DOC-004": "NO-GO",
            "DOC-005": "NO-GO",
            "DOC-006": "CONDITIONAL_GO_LIMITED_SCOPE",
            "DOC-007": "CONDITIONAL_GO",
            "DOC-008": "CONDITIONAL_GO",
            "DOC-009": "NO-GO",
        }

        for doc_code, exp_decision in expected_pilot_decisions.items():
            actual = matrix[doc_code]["pilot_eligibility"]["pilot_decision"]
            assert actual == exp_decision, (
                f"{doc_code} pilot decision mismatch: expected {exp_decision}, got {actual}"
            )

        # Dual IAA studies for DOC-002, 006, 007, 008 must exist with Kappa >= 0.85
        for code, fname, min_k, exp_status in [
            ("DOC-002", "doc002_inter_annotator_agreement.json", 0.85, "CONFIRMED"),
            ("DOC-006", "doc006_inter_annotator_agreement.json", 0.85, "CONDITIONAL_GO_LIMITED_SCOPE"),
            ("DOC-007", "doc007_inter_annotator_agreement.json", 0.85, "CONFIRMED"),
            ("DOC-008", "doc008_inter_annotator_agreement.json", 0.85, "CONFIRMED"),
        ]:
            iaa_data = json.loads((EVAL_DIR / fname).read_text(encoding="utf-8"))
            assert iaa_data["cohen_kappa"] >= min_k
            assert iaa_data["conditional_pass_certification"]["status"] == exp_status

        # Reconciliation file for DOC-002 must exist
        assert (EVAL_DIR / "doc002_adjudication_reconciliation.json").exists()

    def test_sealed_holdout_11_field_provenance_block(self):
        """Verify sealed holdout report contains complete 11-field provenance block + staleness audit fields."""
        report_file = HOLDOUT_DIR / "holdout_evaluation_report.json"
        manifest_file = HOLDOUT_DIR / "holdout_manifest.json"

        assert report_file.exists()
        assert manifest_file.exists()

        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        prov = report_data.get("holdout_provenance")
        assert prov is not None, "Missing holdout_provenance block"

        required_fields = [
            "manifest_path", "manifest_sha256", "sealed_at", "corpus_status",
            "total_documents", "total_gold_rules", "evaluation_mode",
            "synthetic_injections_detected", "leakage_audit_status",
            "holdout_integrity_barrier", "governance_standard",
            "harness_version_at_evaluation", "code_commit_at_evaluation",
            "matches_current_certification_harness", "stale_reason_if_applicable"
        ]
        for field in required_fields:
            assert field in prov, f"Missing required provenance field: {field}"

        actual_manifest_sha = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
        assert prov["manifest_sha256"] == actual_manifest_sha
        assert prov["corpus_status"] == "SEALED_AND_FROZEN"
        assert prov["total_documents"] == 15
        assert prov["total_gold_rules"] == 200
        assert prov["synthetic_injections_detected"] == 0
        assert prov["matches_current_certification_harness"] is True
        assert prov["stale_reason_if_applicable"] is None
        assert "no_tuning_attestation" in prov

    def test_lifecycle_provenance_guard_stages_1_to_8(self):
        """Execute all 8 stages of the cryptographic lifecycle guard."""
        guard = LifecycleProvenanceGuard()
        report = guard.run_lifecycle_barrier()
        assert report["overall_status"] == "ALL_8_STAGES_PASSED"
        assert len(report["stages"]) == 8
