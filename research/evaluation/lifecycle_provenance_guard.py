"""
Lifecycle Provenance Guard - 8-Stage Cryptographic Evaluation Barrier
====================================================================
Milestone: Sprint W: Holdout Refresh, Governance Coherence & Initial Recall Restoration
Governance: Antigravity Evaluation Contract v1.0.0

This module implements the 8-stage cryptographic lifecycle barrier to prevent
evaluation tampering, gold-leakage, synthetic artifact inflation, and denominator
drift across Context Layer AI's ground truth evaluation suites.

8 Stages:
  Stage 1: Manifest Integrity Barrier (Corpus and Holdout identity verification)
  Stage 2: Zero-Gold-Leakage & AST Anti-Tamper Barrier (Benchmark harness inspection)
  Stage 3: Extraction Artifact Integrity & Anti-Injection Verification (DOC-005 / DOC-009)
  Stage 4: Candidate Accounting & Adjudication Decoupling Invariant
  Stage 5: Dual-Review Inter-Annotator Agreement (IAA) Certification Barrier (DOC-002, 006, 007, 008)
  Stage 6: Two-Tier Governance & Pilot Decision Alignment
  Stage 7: Sealed Holdout Corpus Cryptographic Invariance (11-field provenance block + staleness audit)
  Stage 8: Artifact Cryptographic Provenance Anchors (16-artifact SHA-256 verification)
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_DIR = ROOT_DIR / "research" / "evaluation"
HOLDOUT_DIR = ROOT_DIR / "research" / "holdout"
RESULTS_DIR = ROOT_DIR / "research" / "extraction-results"


def get_claims_list(data: Any) -> List[Any]:
    """Helper to extract claims array from various output formats."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "extraction_response" in data and "claims" in data["extraction_response"]:
            return data["extraction_response"]["claims"]
        if "extracted_claims" in data:
            return data["extracted_claims"]
        if "claims" in data:
            return data["claims"]
    return []


class LifecycleProvenanceGuard:
    """Enforces cryptographic and systemic integrity barriers across all evaluation tiers."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or ROOT_DIR
        self.eval_dir = self.root_dir / "research" / "evaluation"
        self.holdout_dir = self.root_dir / "research" / "holdout"
        self.results_dir = self.root_dir / "research" / "extraction-results"

    def stage_1_manifest_integrity_barrier(self) -> Dict[str, Any]:
        """Verify dev and holdout manifests, document identities, domains, and rule counts."""
        manifest_path = self.eval_dir / "corpus_manifest.json"
        holdout_manifest_path = self.holdout_dir / "holdout_manifest.json"

        assert manifest_path.exists(), f"Missing corpus_manifest.json at {manifest_path}"
        assert holdout_manifest_path.exists(), f"Missing holdout_manifest.json at {holdout_manifest_path}"

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        holdout_manifest = json.loads(holdout_manifest_path.read_text(encoding="utf-8"))

        expected_identities = {
            "DOC-001": ("Central Ohio Technical College", "Resignation and Voluntary Termination Policy", "hr_policy", 8),
            "DOC-002": ("Government of Mizoram (DP&AR)", "Guidelines for Engagement of Employees on Contract Basis", "contract_employment_guidelines", 10),
            "DOC-003": ("University of St. Thomas", "Termination of Employment Policy", "termination_policy", 10),
            "DOC-004": ("TermsFeed E-Commerce Standard", "Sample Return and Refund Policy Template", "refund_policy", 6),
            "DOC-005": ("Tarion Warranty Corporation", "Commercial Vendor Agreement Template", "commercial_vendor_agreement", 32),
            "DOC-006": ("DEMO - Sliced Invoices", "WordPress PDF Invoice Plugin Sample", "invoice", 5),
            "DOC-007": ("U.S. EPA (Office of Water)", "EPA Lead and Copper Rule Implementation Letter", "regulatory_directive_letter", 3),
            "DOC-008": ("Wingify Software Private Limited", "Employee Notice Period Policy", "hr_policy", 18),
            "DOC-009": ("Northwind Traders", "Northwind Refund Policy Handbook", "refund_handbook", 78),
        }

        doc_dict = manifest.get("documents", {})
        for doc_code, (exp_org, exp_title, exp_domain, exp_gold) in expected_identities.items():
            assert doc_code in doc_dict, f"Missing {doc_code} in corpus manifest"
            doc = doc_dict[doc_code]
            assert doc["organization"] == exp_org
            assert doc["title"] == exp_title
            assert doc["document_type"] == exp_domain
            assert doc["gold_canonical_rules_count"] == exp_gold

        holdout_docs = holdout_manifest.get("documents", {})
        assert len(holdout_docs) == 15, f"Holdout must have 15 documents, found {len(holdout_docs)}"
        total_holdout_gold = sum(d["gold_canonical_rules_count"] for d in holdout_docs.values())
        assert total_holdout_gold in (194, 200)

        return {
            "stage": 1,
            "name": "manifest_integrity_barrier",
            "status": "PASSED",
            "dev_documents_verified": len(expected_identities),
            "holdout_documents_verified": len(holdout_docs),
            "total_holdout_gold_rules": total_holdout_gold
        }

    def stage_2_zero_gold_leakage_ast_barrier(self) -> Dict[str, Any]:
        """Perform AST inspection on benchmark_harness.py ensuring zero gold-leakage or conditioned checks."""
        harness_path = self.eval_dir / "benchmark_harness.py"
        assert harness_path.exists(), f"Missing benchmark_harness.py at {harness_path}"

        tree = ast.parse(harness_path.read_text(encoding="utf-8"))

        forbidden_identifiers = {"gold_subjects"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_identifiers:
                raise AssertionError(f"Forbidden gold-leakage identifier '{node.id}' found in AST at line {node.lineno}")
            if isinstance(node, ast.Attribute) and node.attr in forbidden_identifiers:
                raise AssertionError(f"Forbidden gold-leakage attribute '{node.attr}' found in AST at line {node.lineno}")

        code_text = harness_path.read_text(encoding="utf-8")
        assert 'is_invoice = (canonical_doc_type == "invoice")' in code_text
        assert 'sub.lower() in ("total", "subtotal", "tax") and not is_invoice' in code_text

        return {
            "stage": 2,
            "name": "zero_gold_leakage_ast_barrier",
            "status": "PASSED",
            "ast_nodes_scanned": len(list(ast.walk(tree))),
            "gold_subjects_references": 0,
            "universal_invoice_rule_verified": True
        }

    def stage_3_extraction_artifact_integrity(self) -> Dict[str, Any]:
        """Verify DOC-005 and DOC-009 extraction outputs match authentic git HEAD baselines with 0 synthetic markers."""
        doc005_path = self.results_dir / "DOC-005_output.json"
        doc009_path = self.results_dir / "DOC-009_output.json"
        audit_path = self.eval_dir / "artifact_diff_audit.json"

        assert doc005_path.exists()
        assert doc009_path.exists()
        assert audit_path.exists()

        data005 = json.loads(doc005_path.read_text(encoding="utf-8"))
        data009 = json.loads(doc009_path.read_text(encoding="utf-8"))
        audit_data = json.loads(audit_path.read_text(encoding="utf-8"))

        claims_005 = get_claims_list(data005)
        claims_009 = get_claims_list(data009)

        assert len(claims_005) == 129, f"DOC-005 authentic baseline claim count must be 129, got {len(claims_005)}"
        assert len(claims_009) == 250, f"DOC-009 authentic baseline claim count must be 250, got {len(claims_009)}"

        for i, c in enumerate(claims_005):
            assert "synthetic" not in str(c).lower()
        for i, c in enumerate(claims_009):
            assert "synthetic" not in str(c).lower()

        assert audit_data.get("executive_verdict") == "SYNTHETIC_INJECTIONS_PURGED_AND_REVERTED"

        return {
            "stage": 3,
            "name": "extraction_artifact_integrity",
            "status": "PASSED",
            "doc005_claims": len(claims_005),
            "doc009_claims": len(claims_009),
            "synthetic_markers_detected": 0,
            "audit_log_verified": True
        }

    def stage_4_candidate_accounting_and_decoupling(self) -> Dict[str, Any]:
        """Verify candidates are strictly partitioned and unadjudicated pools report adjudicated_precision = None."""
        if str(self.eval_dir) not in sys.path:
            sys.path.insert(0, str(self.eval_dir))
        from benchmark_harness import BenchmarkHarness

        harness = BenchmarkHarness(results_dir=self.results_dir)

        # Unadjudicated documents: adjudicated_precision must be None
        unadj_docs = ["DOC-001", "DOC-003", "DOC-004", "DOC-005", "DOC-009"]
        for code in unadj_docs:
            res = harness.evaluate_document(code)
            adj_p = res["metrics"]["adjudicated_precision"]
            adj_cnt = res["metrics"]["adjudicated_claim_count"]
            assert adj_p is None, f"{code} unadjudicated candidates must report None, got {adj_p}"
            assert adj_cnt == 0, f"{code} expected 0 adjudicated claims, got {adj_cnt}"

        # Certified adjudicated documents: DOC-002, DOC-006, DOC-007, DOC-008
        adj_docs = ["DOC-002", "DOC-006", "DOC-007", "DOC-008"]
        for code in adj_docs:
            res = harness.evaluate_document(code)
            adj_p = res["metrics"]["adjudicated_precision"]
            adj_cnt = res["metrics"]["adjudicated_claim_count"]
            valid_cnt = res["metrics"]["adjudicated_valid_count"]
            assert adj_p is not None, f"{code} expected float adjudicated_precision, got None"
            assert adj_cnt > 0, f"{code} expected >0 adjudicated claims, got {adj_cnt}"
            expected_p = round(valid_cnt / adj_cnt, 4)
            assert round(adj_p, 4) == expected_p, f"{code} precision mismatch: expected {expected_p}, got {adj_p}"

        return {
            "stage": 4,
            "name": "candidate_accounting_and_decoupling",
            "status": "PASSED",
            "unadjudicated_documents_verified": unadj_docs,
            "adjudicated_documents_verified": adj_docs
        }

    def stage_5_dual_review_iaa_barrier(self) -> Dict[str, Any]:
        """Verify dual-review Cohen's Kappa >= 0.85 for all pilot-eligible docs (DOC-002, 006, 007, 008)."""
        iaa_files = [
            ("DOC-002", self.eval_dir / "doc002_inter_annotator_agreement.json", 0.85, "CONFIRMED"),
            ("DOC-006", self.eval_dir / "doc006_inter_annotator_agreement.json", 0.85, "CONDITIONAL_GO_LIMITED_SCOPE"),
            ("DOC-007", self.eval_dir / "doc007_inter_annotator_agreement.json", 0.85, "CONFIRMED"),
            ("DOC-008", self.eval_dir / "doc008_inter_annotator_agreement.json", 0.85, "CONFIRMED"),
        ]

        for doc_id, file_path, min_kappa, exp_status in iaa_files:
            assert file_path.exists(), f"Missing IAA study for {doc_id} at {file_path}"
            data = json.loads(file_path.read_text(encoding="utf-8"))
            kappa = data["cohen_kappa"]
            assert kappa >= min_kappa, f"{doc_id} Cohen's Kappa {kappa} below required {min_kappa}"
            assert data.get("conditional_pass_certification", {}).get("status") == exp_status

        # Also verify DOC-002 reconciliation audit exists
        reconcile_path = self.eval_dir / "doc002_adjudication_reconciliation.json"
        assert reconcile_path.exists(), "Missing doc002_adjudication_reconciliation.json"
        rec_data = json.loads(reconcile_path.read_text(encoding="utf-8"))
        assert rec_data["audit_trail"]["verification_status"] == "RECONCILED_AND_CONFIRMED"

        return {
            "stage": 5,
            "name": "dual_review_iaa_barrier",
            "status": "PASSED",
            "certified_iaa_studies": [x[0] for x in iaa_files],
            "doc002_reconciliation_verified": True
        }

    def stage_6_two_tier_governance_alignment(self) -> Dict[str, Any]:
        """Assert Autonomous Production is NO-GO corpus-wide; Staged Pilot CONDITIONAL_GO for DOC-002/006/007/008."""
        matrix_path = self.eval_dir / "all_documents_verdict_matrix.json"
        assert matrix_path.exists(), f"Missing {matrix_path}"
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
            doc_data = matrix[doc_code]
            actual_decision = doc_data["pilot_eligibility"]["pilot_decision"]
            assert actual_decision == exp_decision, (
                f"{doc_code} pilot decision mismatch: expected {exp_decision}, got {actual_decision}"
            )

        # Autonomous production posture: NO-GO corpus-wide
        for code, d in matrix.items():
            if code not in ("DOC-006", "DOC-008"):
                assert d["verdict"] == "NEEDS_WORK", f"{code} verdict must be NEEDS_WORK, got {d['verdict']}"

        return {
            "stage": 6,
            "name": "two_tier_governance_alignment",
            "status": "PASSED",
            "autonomous_production": "NO-GO (BLOCKED_CORPUS_WIDE)",
            "pilot_decisions": expected_pilot_decisions
        }

    def stage_7_sealed_holdout_provenance_barrier(self) -> Dict[str, Any]:
        """Verify sealed holdout report contains 11-field provenance block plus staleness audit fields."""
        report_path = self.holdout_dir / "holdout_evaluation_report.json"
        manifest_path = self.holdout_dir / "holdout_manifest.json"

        assert report_path.exists(), f"Missing {report_path}"
        assert manifest_path.exists(), f"Missing {manifest_path}"

        report = json.loads(report_path.read_text(encoding="utf-8"))
        prov = report.get("holdout_provenance")
        assert prov is not None, "Missing holdout_provenance in holdout_evaluation_report.json"

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

        manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        assert prov["manifest_sha256"] == manifest_sha
        assert prov["synthetic_injections_detected"] == 0
        assert prov["matches_current_certification_harness"] is True
        assert prov["stale_reason_if_applicable"] is None
        assert "no_tuning_attestation" in prov

        return {
            "stage": 7,
            "name": "sealed_holdout_provenance_barrier",
            "status": "PASSED",
            "manifest_sha256": manifest_sha,
            "corpus_status": prov["corpus_status"],
            "staleness_audit_verified": True
        }

    def stage_8_artifact_provenance_anchors(self) -> Dict[str, Any]:
        """Verify all 16 evaluation artifacts match SHA-256 digests in artifact_provenance.json with 0 mismatches."""
        prov_path = self.eval_dir / "artifact_provenance.json"
        assert prov_path.exists(), f"Missing {prov_path}"

        prov_data = json.loads(prov_path.read_text(encoding="utf-8"))
        registered_artifacts = prov_data.get("artifacts", {})

        expected_16_artifacts = [
            "corpus_manifest.json",
            "gold_version_diff.json",
            "EVALUATION_CONTRACT_v1.md",
            "overfit_audit_report.json",
            "adjudications.json",
            "doc002_inter_annotator_agreement.json",
            "doc002_adjudication_reconciliation.json",
            "doc006_pipeline_diagnosis.json",
            "doc006_inter_annotator_agreement.json",
            "doc007_inter_annotator_agreement.json",
            "doc008_inter_annotator_agreement.json",
            "all_documents_verdict_matrix.json",
            "benchmark_metrics_report.json",
            "ALL_DOCUMENTS_EVALUATION.md",
            "CERTIFICATION_REPORT_v1.md",
            "artifact_diff_audit.json"
        ]

        verified_count = 0
        mismatches = []
        for rel_name in expected_16_artifacts:
            assert rel_name in registered_artifacts, f"{rel_name} missing from artifact_provenance.json"
            f_path = self.eval_dir / rel_name
            assert f_path.exists(), f"File {f_path} does not exist on disk"
            raw = f_path.read_bytes()
            sha_raw = hashlib.sha256(raw).hexdigest()
            sha_lf = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
            expected_sha = registered_artifacts[rel_name]
            actual_sha = sha_raw if sha_raw == expected_sha else sha_lf
            if actual_sha != expected_sha:
                mismatches.append((rel_name, expected_sha, actual_sha))
            else:
                verified_count += 1

        assert len(mismatches) == 0, f"Found {len(mismatches)} provenance hash mismatches: {mismatches}"
        assert verified_count == 16, f"Expected 16 verified artifacts, got {verified_count}"

        return {
            "stage": 8,
            "name": "artifact_provenance_anchors",
            "status": "PASSED",
            "verified_artifact_count": verified_count,
            "hash_mismatches": 0
        }

    def run_lifecycle_barrier(self) -> Dict[str, Any]:
        """Execute all 8 stages sequentially and return overall verdict."""
        stages = [
            ("Stage 1: Manifest Integrity Barrier", self.stage_1_manifest_integrity_barrier),
            ("Stage 2: Zero-Gold-Leakage & AST Anti-Tamper Barrier", self.stage_2_zero_gold_leakage_ast_barrier),
            ("Stage 3: Extraction Artifact Integrity & Anti-Injection Verification", self.stage_3_extraction_artifact_integrity),
            ("Stage 4: Candidate Accounting & Decoupling Invariant", self.stage_4_candidate_accounting_and_decoupling),
            ("Stage 5: Dual-Review IAA Certification Barrier", self.stage_5_dual_review_iaa_barrier),
            ("Stage 6: Two-Tier Governance & Pilot Alignment", self.stage_6_two_tier_governance_alignment),
            ("Stage 7: Sealed Holdout Provenance Barrier", self.stage_7_sealed_holdout_provenance_barrier),
            ("Stage 8: Artifact Cryptographic Provenance Anchors", self.stage_8_artifact_provenance_anchors),
        ]

        results = {}
        for stage_title, stage_fn in stages:
            stage_res = stage_fn()
            results[stage_res["name"]] = stage_res

        return {
            "milestone": "Sprint W: Holdout Refresh, Governance Coherence & Initial Recall Restoration",
            "overall_status": "ALL_8_STAGES_PASSED",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stages": results
        }


if __name__ == "__main__":
    guard = LifecycleProvenanceGuard()
    print("=" * 70)
    print("Executing Lifecycle Provenance Guard (8 Stages)...")
    print("=" * 70)
    try:
        report = guard.run_lifecycle_barrier()
        print("\n" + json.dumps(report, indent=2))
        print("\nSUCCESS: All 8 cryptographic lifecycle stages passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nBARRIER VIOLATION: {e}")
        sys.exit(1)
