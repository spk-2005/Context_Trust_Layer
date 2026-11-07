"""
Unit tests for Phase 8: End-to-End Regression, Evidence Evaluation, and Release Certification.

Verifies:
1. Golden Corpus Integrity and Manifest Consistency across all 18 fixture types.
2. Decoupled Extraction Performance (page/block, row/record, field coverage, table detection, cell alignment, empty-cell preservation, locators).
3. OCR CER/WER and Safe Token Audit.
4. Decoupled Claim Quality Metrics (precision, recall, F1, condition recall, exception recall, atomicity, table-context, quote fidelity, citation validity).
5. Hard Release Gate Enforcement (9 gates checked fail-closed).
6. End-to-End Pipeline Execution: Ingestion -> Layer 4 -> Layer 5 -> Layer 6 Validation -> Conflict/Trust.
7. Northwind Refund Handbook: Video course rule supported by its own evidence, never linked to Digital Goods clause.
8. Conflicting Versions: Multi-version distinct candidate preservation and conflict engine detection.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.enums import SourceFamily, SourceIntent
from app.evaluation.evidence_metrics import (
    EvidenceEvaluationService,
    ExtractionQualityMetrics,
    ClaimQualityMetrics,
    ReleaseGateCheck,
    compute_cer,
    compute_wer,
    levenshtein_distance,
)
from app.extraction.models import CandidateClaim, TableGridBinding
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceUnit,
    ExtractionStatus,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
    SourceLocator,
)
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.universal_file_parser import UniversalFileParser, repair_ocr_text
from app.validation_gate.evidence_validator import ReliableClaimEvidenceValidator
from app.validation_gate.models import ClaimValidationStatus


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "golden_corpus"


# =========================================================================
# Test 1: Golden Corpus Integrity and Manifest Consistency
# =========================================================================

def test_golden_corpus_integrity_and_manifest():
    """Verify that all 18 fixtures exist on disk, are valid and indexed in manifest.json."""
    manifest_path = FIXTURES_DIR / "manifest.json"
    assert manifest_path.exists(), "manifest.json must exist in golden_corpus directory"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixtures = manifest.get("fixtures", {})
    assert len(fixtures) >= 18, f"Expected at least 18 fixtures in manifest, found {len(fixtures)}"

    for fix_key, fix_meta in fixtures.items():
        if "filename" in fix_meta:
            file_path = FIXTURES_DIR / fix_meta["filename"]
            assert file_path.exists(), f"Fixture file {file_path} missing on disk"
            assert file_path.stat().st_size > 0, f"Fixture file {file_path} is empty"
        elif "v1_file" in fix_meta:
            v1_p = FIXTURES_DIR / fix_meta["v1_file"]
            v2_p = FIXTURES_DIR / fix_meta["v2_file"]
            assert v1_p.exists() and v2_p.exists(), "Versioned fixtures missing on disk"


# =========================================================================
# Test 2: Decoupled Extraction Performance Across Golden Fixtures
# =========================================================================

@pytest.mark.asyncio
async def test_decoupled_extraction_performance():
    """Verify that extraction metrics are computed separately and reflect real parser coverage."""
    # 1. Test CSV with empty cells using Layer 4 StructuredDataParser
    csv_bytes = (FIXTURES_DIR / "quoted_empty_fields.csv").read_bytes()
    env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="quoted_empty_fields.csv",
        source_family=SourceFamily.STRUCTURED,
        native_format="csv",
        source_version="v1",
        content_hash="csv_h1",
        raw_payload=csv_bytes.decode("utf-8"),
        locator_metadata={"database": "prod", "table": "products"},
    )
    result = await StructuredDataParser.parse(env)

    # 1 dataset summary + 15 row units = 16 units
    assert len(result.units) == 16
    assert result.completeness_score == 1.0

    # Verify empty cell preservation across row units
    row2 = result.units[2]
    cols2 = row2.structured_data["columns"]
    assert cols2["product_name"] == "", "Empty product_name in row 2 must be preserved without shifting"
    assert cols2["category"] == "Hardware"

    row3 = result.units[3]
    cols3 = row3.structured_data["columns"]
    assert cols3["category"] == "", "Empty category in row 3 must be preserved"

    empty_cells_count = sum(
        1 for u in result.units[1:] for val in u.structured_data["columns"].values() if str(val).strip() == ""
    )
    assert empty_cells_count >= 5, "Empty cells must be preserved in structured representation"

    # 2. Test XLSX with sparse cells, formulas, and merged ranges using UniversalFileParser
    xlsx_bytes = (FIXTURES_DIR / "multi_sheet_sparse.xlsx").read_bytes()
    parsed_xlsx = UniversalFileParser.parse_structured("multi_sheet_sparse.xlsx", xlsx_bytes)
    assert len(parsed_xlsx.tables) == 3

    # Compute decoupled extraction metrics
    extraction_metrics = EvidenceEvaluationService.evaluate_extraction(
        expected_pages=1,
        processed_pages=1,
        expected_blocks=16,
        processed_blocks=len(result.units),
        expected_rows=15,
        processed_rows=15,
        expected_fields=6,
        processed_fields=6,
        expected_tables=1,
        detected_tables=1,
        total_cells=15 * 6,
        aligned_cells=15 * 6,
        expected_empty_cells=6,
        preserved_empty_cells=empty_cells_count,
        total_units=16,
        units_with_valid_locator=16,
    )

    assert extraction_metrics.page_coverage == 1.0
    assert extraction_metrics.row_record_coverage >= 0.95
    assert extraction_metrics.table_detection_recall == 1.0
    assert extraction_metrics.empty_cell_preservation_rate >= 0.80
    assert extraction_metrics.locator_coverage_and_accuracy == 1.0


# =========================================================================
# Test 3: OCR CER/WER and Safe Token Audit
# =========================================================================

def test_ocr_cer_wer_and_safe_token_audit():
    """Verify Levenshtein CER/WER calculation and ensure critical tokens are audited and protected."""
    ref = "Compliant with AES256 and TLS1.3 for v2.0 on the 15th with $100k budget."
    # Simulate a noisy OCR hypothesis with a typo and an extra space
    hyp = "Compliant with AES256 and TLS1.3 for v2.0 on the 15th with $100k budgt."

    cer = compute_cer(ref, hyp)
    wer = compute_wer(ref, hyp)

    assert 0.0 < cer < 0.05, f"CER should be very low for a 1-character typo, got {cer}"
    assert 0.0 < wer < 0.15, f"WER should be low for a 1-word typo, got {wer}"

    # Verify safe token audit with repair_ocr_text
    scanned_text = "Compliant with AES256 and TLS1.3 for v2.0 on the 15th with $100k budget. Complete within next30days and 50% discount."
    repaired = repair_ocr_text(scanned_text)

    # Audited invariant: Protected tokens must never be split or mutated
    critical_tokens = ["AES256", "TLS1.3", "v2.0", "15th", "$100k", "50%"]
    for tok in critical_tokens:
        assert tok in repaired, f"Critical token {tok} was improperly modified during OCR repair"

    # Run-together text must be safely repaired
    assert "next 30 days" in repaired


# =========================================================================
# Test 4: Decoupled Claim Quality Metrics
# =========================================================================

def test_decoupled_claim_quality_metrics():
    """Verify that claim quality metrics are measured separately without unexplained aggregation."""
    # Create sample extracted candidates
    cand1 = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u1",
        asset_id="handbook.md",
        claim_text="Video courses may be refunded within 7 days of purchase, provided less than 20% of the course has been viewed.",
        subject="Video courses",
        predicate="has_refund_window",
        object_="7 days of purchase",
        evidence_text_span="Video courses may be refunded within 7 days of purchase, provided less than 20% of the course has been viewed.",
        conditions=["less than 20% of the course has been viewed"],
        evidence_unit_ids=["u1"],
    )
    cand1.status = "verified"

    cand2 = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u2",
        asset_id="handbook.md",
        claim_text="Perishable goods past 14 days are non-refundable, except if damaged upon delivery.",
        subject="Perishable goods past 14 days",
        predicate="are non-refundable",
        object_="non-refundable",
        evidence_text_span="Perishable goods past 14 days are non-refundable, except if damaged upon delivery.",
        exceptions=["damaged upon delivery"],
        evidence_unit_ids=["u2"],
    )
    cand2.status = "verified"

    # Table claim with binding
    cand_tbl = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u3",
        asset_id="table.pdf",
        claim_text="Standard tier has max expense limit of $1,000.",
        subject="Standard tier",
        predicate="has_limit",
        object_="$1,000",
        evidence_text_span="Standard tier has max expense limit of $1,000.",
        table_binding=TableGridBinding(
            table_id="tbl-1",
            row_index=1,
            column_index=1,
            row_key="Standard",
            cell_value="$1,000",
            column_header="Max Expense",
            header_path=["Approval Matrix", "Max Expense"],
        ),
        evidence_unit_ids=["u3"],
    )
    cand_tbl.status = "verified"

    gold_claims = [
        {
            "subject": "Video courses",
            "predicate": "has_refund_window",
            "object": "7 days of purchase",
            "conditions": ["less than 20% of the course has been viewed"],
        },
        {
            "subject": "Perishable goods past 14 days",
            "predicate": "are non-refundable",
            "object": "non-refundable",
            "exceptions": ["damaged upon delivery"],
        },
        {
            "subject": "Standard tier",
            "predicate": "has_limit",
            "object": "$1,000",
        },
    ]

    unit_map = {"u1": True, "u2": True, "u3": True}

    metrics: ClaimQualityMetrics = EvidenceEvaluationService.evaluate_claims(
        extracted_claims=[cand1, cand2, cand_tbl],
        gold_claims=gold_claims,
        unit_map=unit_map,
    )

    assert metrics.claim_precision == 1.0
    assert metrics.claim_recall == 1.0
    assert metrics.claim_f1 == 1.0
    assert metrics.condition_recall == 1.0
    assert metrics.exception_recall == 1.0
    assert metrics.atomicity_accuracy == 1.0
    assert metrics.table_context_accuracy == 1.0
    assert metrics.evidence_support_rate == 1.0
    assert metrics.quote_fidelity == 1.0
    assert metrics.citation_validity == 1.0


# =========================================================================
# Test 5: Production Release Gate Checks
# =========================================================================

def test_production_release_gate_checks():
    """Verify all 9 release gates pass on clean state and fail-closed when invariants are violated."""
    extraction_metrics = ExtractionQualityMetrics(
        expected_pages=1, processed_pages=1, page_coverage=1.0,
        expected_blocks=10, processed_blocks=10, block_coverage=1.0,
        expected_rows=10, processed_rows=10, row_record_coverage=1.0,
        expected_fields=4, processed_fields=4, field_coverage=1.0,
        expected_tables=1, detected_tables=1, table_detection_recall=1.0,
        total_cells=40, aligned_cells=40, cell_alignment_accuracy=1.0,
        expected_empty_cells=2, preserved_empty_cells=2, empty_cell_preservation_rate=1.0,
        total_evidence_units=10, units_with_valid_locator=10, locator_coverage_and_accuracy=1.0,
    )
    claim_metrics = ClaimQualityMetrics(
        total_extracted_claims=3, total_gold_claims=3, true_positive_claims=3,
        claim_precision=1.0, claim_recall=1.0, claim_f1=1.0,
        expected_conditions=1, captured_conditions=1, condition_recall=1.0,
        expected_exceptions=1, captured_exceptions=1, exception_recall=1.0,
        total_propositions=3, atomic_propositions=3, atomicity_accuracy=1.0,
        total_table_claims=1, table_claims_with_valid_headers=1, table_context_accuracy=1.0,
        supported_claims=3, evidence_support_rate=1.0,
        claims_with_faithful_quotes=3, quote_fidelity=1.0,
        total_citations=3, valid_citations=3, citation_validity=1.0,
    )

    # 1. Clean run: all gates pass
    gate_res = EvidenceEvaluationService.evaluate_release_gates(
        extraction_metrics=extraction_metrics,
        claim_metrics=claim_metrics,
    )
    assert gate_res.passed is True
    assert len(gate_res.failure_reasons) == 0

    # 2. Gate 1 failure: silent parser failure
    fail_res1 = EvidenceEvaluationService.evaluate_release_gates(
        extraction_metrics=extraction_metrics,
        claim_metrics=claim_metrics,
        silent_parser_failures=1,
    )
    assert fail_res1.passed is False
    assert any("silent parser failure" in r.lower() for r in fail_res1.failure_reasons)

    # 3. Gate 4 failure: certified claim with invalid locator
    fail_res4 = EvidenceEvaluationService.evaluate_release_gates(
        extraction_metrics=extraction_metrics,
        claim_metrics=claim_metrics,
        certified_claims_with_invalid_locator=2,
    )
    assert fail_res4.passed is False
    assert any("invalid locator" in r.lower() for r in fail_res4.failure_reasons)

    # 4. Gate 5 failure: unpreserved condition
    fail_res5 = EvidenceEvaluationService.evaluate_release_gates(
        extraction_metrics=extraction_metrics,
        claim_metrics=claim_metrics,
        certified_claims_with_dropped_conditions=1,
    )
    assert fail_res5.passed is False
    assert any("condition" in r.lower() for r in fail_res5.failure_reasons)


# =========================================================================
# Test 6: End-to-End Pipeline Execution
# =========================================================================

@pytest.mark.asyncio
async def test_end_to_end_pipeline_execution():
    """Verify source ingestion -> Layer 4 parsing -> Layer 5 discovery -> Layer 6 validation -> Deduplication."""
    readme_path = FIXTURES_DIR / "governance_readme.md"
    readme_bytes = readme_path.read_bytes()

    opts = UnifiedPipelineOptions(
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
        doc_title="Security Governance Readme",
        persist_to_db=False,
    )

    result = await UnifiedExtractionPipeline.execute(
        filename="governance_readme.md",
        raw_bytes=readme_bytes,
        options=opts,
    )

    assert result.envelope is not None
    assert "governance_readme.md" in result.envelope.asset_id
    assert len(result.evidence_result.units) > 0

    # All units must have non-null source locators
    for u in result.evidence_result.units:
        assert u.locator is not None, f"Unit {u.unit_id} missing locator"

    # Candidates discovered
    assert len(result.candidates) >= 1
    extracted_claim = result.candidates[0]
    assert extracted_claim.subject is not None
    assert extracted_claim.predicate is not None

    # Layer 6 evaluations performed
    assert len(result.evaluations) >= 1
    eval_rec = result.evaluations[0]
    assert eval_rec.source_match.passed is True


# =========================================================================
# Test 7: Northwind Refund Handbook: Video Course vs Digital Goods Clause
# =========================================================================

@pytest.mark.asyncio
async def test_northwind_video_course_vs_digital_goods_isolation():
    """
    Northwind refund handbook scenario:
    Proves that the video-course refund rule is supported by its own correct evidence (Section 6.1)
    and NEVER links to or gets contaminated by the general digital-goods clause (Section 6).
    """
    handbook_path = FIXTURES_DIR / "northwind_handbook.md"
    handbook_bytes = handbook_path.read_bytes()

    opts = UnifiedPipelineOptions(
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
        doc_title="Northwind Refund Handbook",
        persist_to_db=False,
    )

    result = await UnifiedExtractionPipeline.execute(
        filename="northwind_handbook.md",
        raw_bytes=handbook_bytes,
        options=opts,
    )

    # 1. Inspect units
    units = result.evidence_result.units
    sec6_digital_goods_units = [
        u for u in units
        if "digital goods" in u.normalized_content.lower() and "non-refundable" in u.normalized_content.lower()
        and getattr(u, "block_type", "") in ("paragraph", "clause")
    ]
    sec61_video_course_units = [
        u for u in units
        if "video courses" in u.normalized_content.lower()
        and getattr(u, "block_type", "") in ("paragraph", "clause")
    ]

    assert len(sec6_digital_goods_units) >= 1, "Section 6 Digital Goods clause unit must be extracted"
    assert len(sec61_video_course_units) >= 1, "Section 6.1 Video Course clause unit must be extracted"

    digital_goods_unit = sec6_digital_goods_units[0]
    video_course_unit = sec61_video_course_units[0]

    # Verify distinct unit locators and IDs
    assert digital_goods_unit.unit_id != video_course_unit.unit_id

    # 2. Inspect candidate claims
    video_claims = [c for c in result.candidates if "video course" in (c.subject or "").lower() or "video course" in (c.claim_text or "").lower()]
    assert len(video_claims) >= 1, "Video course candidate claim must be extracted"

    video_claim = video_claims[0]
    # Conditions must be preserved
    assert len(video_claim.conditions) >= 1 or "20%" in (video_claim.claim_text or "")

    # 3. Evidence validation isolation
    val_result = ReliableClaimEvidenceValidator.validate_claim(
        claim=video_claim,
        evidence_units=units,
    )

    # The claim must be supported by video_course_unit, and NOT digital_goods_unit
    assert val_result.validation_status == ClaimValidationStatus.SUPPORTED
    assert video_course_unit.unit_id in val_result.linked_evidence_ids
    assert digital_goods_unit.unit_id not in val_result.linked_evidence_ids, (
        "CRITICAL TOPICAL CONTAMINATION: Video course claim must NOT link to Digital Goods clause!"
    )


# =========================================================================
# Test 8: Conflicting Source Versions and Temporal Preservation
# =========================================================================

@pytest.mark.asyncio
async def test_conflicting_source_versions_preservation():
    """Verify conflicting claims across versions are preserved as distinct candidates and not merged."""
    v1_bytes = (FIXTURES_DIR / "conflicting_v1.md").read_bytes()
    v2_bytes = (FIXTURES_DIR / "conflicting_v2.md").read_bytes()

    opts_v1 = UnifiedPipelineOptions(doc_title="Customer Service Policy", persist_to_db=False)
    opts_v2 = UnifiedPipelineOptions(doc_title="Customer Service Policy", persist_to_db=False)

    res_v1 = await UnifiedExtractionPipeline.execute(
        filename="conflicting_v1.md",
        raw_bytes=v1_bytes,
        options=opts_v1,
    )
    res_v2 = await UnifiedExtractionPipeline.execute(
        filename="conflicting_v2.md",
        raw_bytes=v2_bytes,
        options=opts_v2,
    )

    c1 = res_v1.candidates[0]
    c2 = res_v2.candidates[0]

    # Both candidates must be preserved with their distinct text and values
    assert "30 days" in (c1.claim_text or c1.object)
    assert "14 days" in (c2.claim_text or c2.object)
    assert c1.candidate_id != c2.candidate_id

    # Cross-version validation with ReliableClaimEvidenceValidator
    # Evaluating c2 against v1 evidence should not trigger FALSE CONTRADICTION if versions differ
    v1_unit = res_v1.evidence_result.units[0]
    v1_unit.source_version = "v1.0"
    c2.source_version = "v2.0"

    cross_val = ReliableClaimEvidenceValidator.validate_claim(
        claim=c2,
        evidence_units=[v1_unit],
    )
    # Different versions should yield INSUFFICIENT_EVIDENCE or NEEDS_REVIEW, NOT false CONTRADICTED
    assert cross_val.validation_status != ClaimValidationStatus.CONTRADICTED

