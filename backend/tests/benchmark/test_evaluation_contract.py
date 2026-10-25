"""
Test suite enforcing Context Layer AI Evaluation Contract v1.
"""

import json
from pathlib import Path
import pytest
from research.evaluation.benchmark_harness import BenchmarkHarness

EVAL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "research" / "evaluation"

def test_contract_document_exists():
    contract_file = EVAL_DIR / "EVALUATION_CONTRACT_v1.md"
    assert contract_file.exists(), "EVALUATION_CONTRACT_v1.md is missing"
    text = contract_file.read_text(encoding="utf-8")
    assert "PASS (Unconditional Production Gate)" in text
    assert "CONDITIONAL_PASS (Staged Deployment Gate)" in text
    assert "Closed Candidate Accounting" in text

def test_unified_quality_gate_thresholds_invariant():
    """Thresholds in BenchmarkHarness must strictly equal contract v1 values."""
    harness = BenchmarkHarness()
    thresh = harness.THRESHOLDS
    assert thresh["pass"]["min_full_recall"] == 0.90
    assert thresh["pass"]["min_full_precision"] == 0.90
    assert thresh["pass"]["min_subject_acc"] == 0.95
    assert thresh["pass"]["max_malformed"] == 0.00
    assert thresh["pass"]["min_traceability"] == 1.00

def test_match_tiers_admissibility():
    """Matcher emitted tiers must be strictly recognized under Contract v1."""
    harness = BenchmarkHarness()
    res = harness.evaluate_document("DOC-008")
    valid_tiers = {
        "FULL_MATCH",
        "PARTIAL_OBJECT_CAPTURE_PENDING_REVIEW",
        "ACCEPTED_PARTIAL_MATCH",
        "WRONG_PREDICATE",
        "WRONG_OBJECT",
        "WRONG_SUBJECT",
        "WRONG_MODALITY",
        "RAW_DISCOVERY_MATCH",
        "MISSING"
    }
    for cid, diag in res["claim_classifications"].items():
        assert diag["match_tier"] in valid_tiers, f"Unrecognized match tier: {diag['match_tier']}"


def test_manifest_identity_enforcement():
    """All 9 development documents must exist in corpus_manifest.json with valid metadata and matching gold SHA256."""
    harness = BenchmarkHarness()
    assert len(harness.manifest.get("documents", {})) == 9, "corpus_manifest.json must contain exactly 9 documents"
    for i in range(1, 10):
        code = f"DOC-00{i}"
        meta = harness.manifest["documents"].get(code)
        assert meta is not None, f"Document {code} missing from manifest"
        assert meta["title"] and len(meta["title"].strip()) > 0
        assert meta["organization"] and len(meta["organization"].strip()) > 0
        assert meta["document_type"] and len(meta["document_type"].strip()) > 0
        assert meta["source_sha256"] and len(meta["source_sha256"]) == 64
        assert meta["gold_sha256"] and len(meta["gold_sha256"]) == 64

        # Validate that evaluate_document successfully resolves and validates hashes
        res = harness.evaluate_document(code)
        assert res["title"] == meta["title"]
        assert res["organization"] == meta["organization"]
        assert res["document_type"] == meta["document_type"]


def test_unknown_document_raises_manifest_error():
    """Evaluating an unregistered document must raise ValueError under manifest barrier."""
    harness = BenchmarkHarness()
    with pytest.raises(ValueError, match="is not registered in immutable corpus_manifest.json"):
        harness.evaluate_document("DOC-999")


def test_doc008_immutable_identity_invariants():
    """DOC-008 must strictly evaluate to Wingify Employee Notice Period Policy with 18 gold canonical rules."""
    harness = BenchmarkHarness()
    doc008_meta = harness.manifest["documents"]["DOC-008"]
    assert doc008_meta["title"] == "Employee Notice Period Policy"
    assert doc008_meta["organization"] == "Wingify Software Private Limited"
    assert doc008_meta["gold_canonical_rules_count"] == 18

    res = harness.evaluate_document("DOC-008")
    assert res["title"] == "Employee Notice Period Policy"
    assert res["organization"] == "Wingify Software Private Limited"
    assert res["counts"]["total_gold_canonical_rules"] == 18


def test_two_tier_quality_gate_contract_definitions():
    """EVALUATION_CONTRACT_v1.md must formalize both Pilot-Readiness and Production-Readiness gates."""
    contract_file = EVAL_DIR / "EVALUATION_CONTRACT_v1.md"
    text = contract_file.read_text(encoding="utf-8")
    assert "Pilot-Readiness Gate" in text, "Pilot-Readiness Gate definition missing from contract"
    assert "Production-Readiness Gate" in text, "Production-Readiness Gate definition missing from contract"
    assert "adjudicated_precision >= 80" in text.lower() or "adjudicated validity precision >= 80" in text.lower()
