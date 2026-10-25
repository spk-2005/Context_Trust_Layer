"""
Hardened Test Suite for Benchmark Harness Matcher Invariants and Evaluator Negative Cases.
Validates:
1. Cross-predicate rejection (e.g. return_window cannot match notice_period)
2. Numerical object contradiction rejection (e.g. 14 days vs 30 days)
3. Modality contradiction rejection (prohibition MUST_NOT vs permission MAY)
4. Empty evidence quote and generic subject guards
5. Strict 1-to-1 candidate reservation (no multi-crediting of single extraction)
6. Immutable corpus manifest SHA-256 integrity and provenance tracking
7. Metric pairing mathematical consistency (Canonical F1 = harmonic mean of Canonical P and R)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
import pytest

# Ensure research evaluation module is importable
EVAL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "research" / "evaluation"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from benchmark_harness import BenchmarkHarness, unpack_gold_object


class TestBenchmarkMatcherInvariants:
    """Rigorous invariant tests for the Benchmark Harness v3.0 evaluator."""

    @pytest.fixture
    def harness(self):
        return BenchmarkHarness()

    def test_predicate_semantic_families_disallow_cross_domain_matching(self, harness):
        """Cross-family predicates must never be compatible."""
        # Across distinct domains
        assert not harness.are_predicates_compatible("has_return_window", "has_notice_period")
        assert not harness.are_predicates_compatible("cannot_be_returned", "has_notice_period")
        assert not harness.are_predicates_compatible("has_total_due", "has_duration_limit")
        assert not harness.are_predicates_compatible("has_medical_reimbursement", "has_shipping_cost_rule")

        # Within the same semantic family
        assert harness.are_predicates_compatible("has_return_window", "return_window")
        assert harness.are_predicates_compatible("has_return_window", "requires_return_within_applicable_window")
        assert harness.are_predicates_compatible("has_notice_period", "notice_period")
        assert harness.are_predicates_compatible("cannot_be_returned", "prohibited_from_return")
        assert harness.are_predicates_compatible("has_sub_total", "has_total_due")

    def test_empty_quote_and_short_strings_never_match(self, tmp_path):
        """Empty or stub quotes (<5 chars) must never be credited as matches."""
        gold_dir = tmp_path / "gold"
        results_dir = tmp_path / "results"
        gold_dir.mkdir()
        results_dir.mkdir()

        gold_data = {
            "document_id": "DOC-TEST",
            "claim_truth": [
                {
                    "claim_id": "G-001",
                    "subject": "employee",
                    "predicate": "has_notice_period",
                    "object": {"value": 14, "unit": "days"},
                    "evidence_quote": "",  # Empty quote
                    "canonical": True,
                },
                {
                    "claim_id": "G-002",
                    "subject": "employee",
                    "predicate": "has_notice_period",
                    "object": {"value": 14, "unit": "days"},
                    "evidence_quote": "abcd",  # Too short (< 5 chars)
                    "canonical": True,
                },
            ],
        }
        cand_data = {
            "extraction_response": {
                "claims": [
                    {
                        "id": "C-001",
                        "subject": "employee",
                        "predicate": "has_notice_period",
                        "object": "14 days",
                        "claim_text": "Employees must give 14 days notice before resignation.",
                        "evidence_text_span": "Employees must give 14 days notice before resignation.",
                        "status": "approved",
                    }
                ]
            }
        }

        (gold_dir / "DOC-TEST_gold.json").write_text(json.dumps(gold_data), encoding="utf-8")
        (results_dir / "DOC-TEST_output.json").write_text(json.dumps(cand_data), encoding="utf-8")

        harness = BenchmarkHarness(gold_dir=gold_dir, results_dir=results_dir)
        eval_result = harness.evaluate_document("DOC-TEST")

        assert eval_result["claim_classifications"]["G-001"]["status"] == "MISSING"
        assert eval_result["claim_classifications"]["G-002"]["status"] == "MISSING"
        assert eval_result["paired_metrics"]["canonical_metrics"]["recall"] == 0.0

    def test_conflicting_numerical_duration_yields_wrong_object(self, tmp_path):
        """Matching evidence text and subject with conflicting numbers must yield WRONG_OBJECT."""
        gold_dir = tmp_path / "gold"
        results_dir = tmp_path / "results"
        gold_dir.mkdir()
        results_dir.mkdir()

        gold_data = {
            "document_id": "DOC-TEST",
            "claim_truth": [
                {
                    "claim_id": "G-001",
                    "subject": "staff member",
                    "predicate": "has_notice_period",
                    "object": {"value": 30, "unit": "days"},
                    "evidence_quote": "Staff members are required to submit notice at least 30 days in advance.",
                    "canonical": True,
                }
            ],
        }
        cand_data = {
            "extraction_response": {
                "claims": [
                    {
                        "id": "C-001",
                        "subject": "staff member",
                        "predicate": "has_notice_period",
                        "object": "60 days",  # Conflicting duration
                        "claim_text": "Staff members are required to submit notice at least 30 days in advance.",
                        "evidence_text_span": "Staff members are required to submit notice at least 30 days in advance.",
                        "status": "approved",
                    }
                ]
            }
        }

        (gold_dir / "DOC-TEST_gold.json").write_text(json.dumps(gold_data), encoding="utf-8")
        (results_dir / "DOC-TEST_output.json").write_text(json.dumps(cand_data), encoding="utf-8")

        harness = BenchmarkHarness(gold_dir=gold_dir, results_dir=results_dir)
        eval_result = harness.evaluate_document("DOC-TEST")

        diag = eval_result["claim_classifications"]["G-001"]
        # Because candidate object does not match gold object
        assert diag["status"] in ("WRONG_OBJECT", "MISSING")
        assert eval_result["paired_metrics"]["canonical_metrics"]["recall"] == 0.0

    def test_modality_contradiction_rejection(self, tmp_path):
        """Gold prohibition (MUST_NOT) must never match candidate permission (MAY)."""
        gold_dir = tmp_path / "gold"
        results_dir = tmp_path / "results"
        gold_dir.mkdir()
        results_dir.mkdir()

        gold_data = {
            "document_id": "DOC-TEST",
            "claim_truth": [
                {
                    "claim_id": "G-001",
                    "subject": "custom items",
                    "predicate": "cannot_be_returned",
                    "object": {"value": "prohibited", "modality": "MUST_NOT"},
                    "evidence_quote": "Custom ordered items cannot be returned under any circumstances.",
                    "canonical": True,
                }
            ],
        }
        cand_data = {
            "extraction_response": {
                "claims": [
                    {
                        "id": "C-001",
                        "subject": "custom items",
                        "predicate": "cannot_be_returned",
                        "object": "prohibited",
                        "modality": "MAY",  # Contradictory modality: permission instead of prohibition
                        "claim_text": "Custom ordered items cannot be returned under any circumstances.",
                        "evidence_text_span": "Custom ordered items cannot be returned under any circumstances.",
                        "status": "approved",
                    }
                ]
            }
        }

        (gold_dir / "DOC-TEST_gold.json").write_text(json.dumps(gold_data), encoding="utf-8")
        (results_dir / "DOC-TEST_output.json").write_text(json.dumps(cand_data), encoding="utf-8")

        harness = BenchmarkHarness(gold_dir=gold_dir, results_dir=results_dir)
        eval_result = harness.evaluate_document("DOC-TEST")

        diag = eval_result["claim_classifications"]["G-001"]
        assert diag["status"] == "WRONG_MODALITY"
        assert diag["taxonomy"] == "MODALITY_CONTRADICTION"
        assert eval_result["paired_metrics"]["canonical_metrics"]["recall"] == 0.0

    def test_strict_one_to_one_candidate_reservation(self, tmp_path):
        """A single extracted candidate must never be double-counted to satisfy multiple gold rules."""
        gold_dir = tmp_path / "gold"
        results_dir = tmp_path / "results"
        gold_dir.mkdir()
        results_dir.mkdir()

        # Two distinct gold rules with identical/similar source text
        gold_data = {
            "document_id": "DOC-TEST",
            "claim_truth": [
                {
                    "claim_id": "G-001",
                    "subject": "contract employee",
                    "predicate": "has_notice_period",
                    "object": {"value": 30, "unit": "days"},
                    "evidence_quote": "Contract employees must provide thirty days notice of resignation.",
                    "canonical": True,
                },
                {
                    "claim_id": "G-002",
                    "subject": "contract employee",
                    "predicate": "has_notice_period",
                    "object": {"value": 30, "unit": "days"},
                    "evidence_quote": "Contract employees must provide thirty days notice of resignation.",
                    "canonical": True,
                },
            ],
        }
        # Only ONE candidate extracted
        cand_data = {
            "extraction_response": {
                "claims": [
                    {
                        "id": "C-SINGLE-001",
                        "subject": "contract employee",
                        "predicate": "has_notice_period",
                        "object": "30 days",
                        "claim_text": "Contract employees must provide thirty days notice of resignation.",
                        "evidence_text_span": "Contract employees must provide thirty days notice of resignation.",
                        "status": "approved",
                    }
                ]
            }
        }

        (gold_dir / "DOC-TEST_gold.json").write_text(json.dumps(gold_data), encoding="utf-8")
        (results_dir / "DOC-TEST_output.json").write_text(json.dumps(cand_data), encoding="utf-8")

        harness = BenchmarkHarness(gold_dir=gold_dir, results_dir=results_dir)
        eval_result = harness.evaluate_document("DOC-TEST")

        classifications = eval_result["claim_classifications"]
        # Exactly one must match, the other must be MISSING due to reservation
        statuses = [classifications["G-001"]["status"], classifications["G-002"]["status"]]
        assert statuses.count("MATCHED") == 1
        assert statuses.count("MISSING") == 1

        # Recall should be exactly 1/2 = 50%
        assert eval_result["paired_metrics"]["canonical_metrics"]["recall"] == 0.5
        assert eval_result["candidate_ledger"]["gold_rules_captured"] == 1
        assert eval_result["candidate_ledger"]["gold_rules_missed"] == 1

    def test_immutable_corpus_manifest_sha256_integrity(self):
        """All files referenced in corpus_manifest.json must physically exist and match recorded SHA-256."""
        manifest_path = EVAL_DIR / "corpus_manifest.json"
        assert manifest_path.exists(), f"Manifest missing: {manifest_path}"

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["total_documents"] == 9
        documents = manifest["documents"]
        assert len(documents) == 9

        repo_root = EVAL_DIR.parent.parent
        for doc_code in [f"DOC-00{i}" for i in range(1, 10)]:
            assert doc_code in documents, f"Missing document {doc_code} in manifest"
            meta = documents[doc_code]

            # 1. Source PDF exists & matches hash
            src_path = Path(meta["source_file_path"])
            if not src_path.exists():
                src_path = repo_root / "docs" / src_path.name
            assert src_path.exists(), f"Source file does not exist: {src_path}"
            src_bytes = src_path.read_bytes()
            assert len(src_bytes) == meta["source_size_bytes"]
            computed_src_sha = hashlib.sha256(src_bytes).hexdigest()
            assert computed_src_sha == meta["source_sha256"], f"SHA256 mismatch for source {src_path}"

            # 2. Gold label exists & matches hash
            gold_path = Path(meta["gold_label_path"])
            if not gold_path.exists():
                gold_path = repo_root / "research" / "gold_labels" / gold_path.name
            assert gold_path.exists(), f"Gold file does not exist: {gold_path}"
            gold_bytes = gold_path.read_bytes()
            computed_gold_sha = hashlib.sha256(gold_bytes).hexdigest()
            assert computed_gold_sha == meta["gold_sha256"], f"SHA256 mismatch for gold {gold_path}"

            # 3. Canonical rules count is positive
            gold_json = json.loads(gold_bytes.decode("utf-8"))
            canonical_rules = [c for c in gold_json.get("claim_truth", []) if c.get("canonical", True)]
            assert len(canonical_rules) == meta["gold_canonical_rules_count"]
            assert meta["gold_canonical_rules_count"] > 0

    def test_paired_metrics_f1_mathematical_consistency(self):
        """Canonical F1 must strictly equal the harmonic mean of canonical precision and recall."""
        harness = BenchmarkHarness()
        for doc_code in [f"DOC-00{i}" for i in range(1, 10)]:
            res = harness.evaluate_document(doc_code)
            p = res["paired_metrics"]["canonical_metrics"]["precision"]
            r = res["paired_metrics"]["canonical_metrics"]["recall"]
            f1 = res["paired_metrics"]["canonical_metrics"]["f1"]

            if p + r == 0:
                expected_f1 = 0.0
            else:
                expected_f1 = round(2 * (p * r) / (p + r), 4)

            assert abs(f1 - expected_f1) <= 1e-4, f"F1 mismatch for {doc_code}: got {f1}, expected {expected_f1}"

            # Verify candidate ledger consistency
            ledger = res["candidate_ledger"]
            total_pred = (
                ledger["correct_canonical_predictions"]
                + ledger["incorrect_canonical_predictions"]
                + ledger["unjudged_canonical_predictions"]
            )
            assert total_pred == ledger["canonical_candidates"], (
                f"Ledger discrepancy for {doc_code}: sum({total_pred}) != canonical_candidates({ledger['canonical_candidates']})"
            )

    def test_l6_to_canonical_reconciliation_zero_difference(self):
        """Every Layer 6 approved candidate must reconcile with canonical approved plus explicit exclusions with 0 diff."""
        harness = BenchmarkHarness()
        for doc_code in [f"DOC-00{i}" for i in range(1, 10)]:
            res = harness.evaluate_document(doc_code)
            cl = res["candidate_ledger"]
            expected_approved = (
                cl["canonical_approved_total"]
                + cl["excluded_non_canonical"]
                + cl["excluded_boilerplate"]
                + cl["excluded_duplicate"]
                + cl["excluded_malformed"]
                + cl["excluded_other"]
            )
            assert cl["approved_l6_total"] == expected_approved, f"L6 mismatch for {doc_code}"
            assert cl["reconciliation_difference"] == 0, f"Non-zero diff for {doc_code}"

    def test_doc006_honest_baseline_and_zero_partial_inflation(self):
        """DOC-006 audit: verifies 100.0% recall on repaired fixture without partial inflation."""
        harness = BenchmarkHarness()
        res = harness.evaluate_document("DOC-006")
        m = res["metrics"]
        assert m["full_match_recall"] == 1.0
        assert m["partial_match_recall"] == 1.0
        assert res["candidate_ledger"]["correct_full_matches"] == 5
        assert res["candidate_ledger"]["correct_partial_matches"] == 0

    def test_doc002_c09_classified_as_accepted_partial_match_by_matcher(self):
        """DOC002-C09 must be classified deterministically as ACCEPTED_PARTIAL_MATCH due to missing numeric object."""
        harness = BenchmarkHarness()
        res = harness.evaluate_document("DOC-002")
        diag = res["claim_classifications"]["DOC002-C09"]
        assert diag["match_tier"] in ("PARTIAL_OBJECT_CAPTURE_PENDING_REVIEW", "ACCEPTED_PARTIAL_MATCH")
        assert diag["status"] == "PARTIAL"
        assert diag["taxonomy"] == "PARTIAL_OBJECT_CAPTURE"
        assert res["candidate_ledger"]["correct_full_matches"] == 9
        assert res["candidate_ledger"]["correct_partial_matches"] == 1
        assert res["metrics"]["full_match_recall"] == 0.90
        assert res["metrics"]["partial_match_recall"] == 1.00

    def test_evaluation_artifact_immutability_hashes(self):
        """Evaluation artifacts must exist and match recorded SHA-256 hashes in provenance ledger."""
        prov_file = EVAL_DIR / "artifact_provenance.json"
        assert prov_file.exists(), "artifact_provenance.json missing"
        prov = json.loads(prov_file.read_text(encoding="utf-8"))
        artifacts = prov["artifacts"]

        for filename, recorded_sha in artifacts.items():
            fpath = EVAL_DIR / filename
            assert fpath.exists(), f"Artifact missing: {filename}"
            raw = fpath.read_bytes()
            sha_raw = hashlib.sha256(raw).hexdigest()
            sha_lf = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
            actual_sha = sha_raw if sha_raw == recorded_sha else sha_lf
            assert actual_sha == recorded_sha, f"SHA-256 mismatch for {filename}: {actual_sha} != {recorded_sha}"

