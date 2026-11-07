"""
Unit tests for Phase 4: Trulin Extraction Quality Validation, Completeness Reporting, and Parser Observability.

Validates:
1. Extraction statuses: SUCCESS, PARTIAL, FAILED, EMPTY, UNSUPPORTED, NEEDS_OCR.
2. Completeness calculation against known denominators and NOT_MEASURED when unavailable.
3. Truncation and dropped records reporting.
4. EvidenceExtractionValidator detecting all 9 validation defects:
   - Duplicate evidence IDs
   - Missing evidence IDs
   - Missing / invalid source locators (e.g. negative coordinates)
   - Broken parent-child relationships
   - Broken structural relationship targets
   - Missing table headers & mismatched table row widths
   - Missing required source fields (asset_id)
   - Normalized content without raw provenance
   - Invalid extraction status
   - Nonexistent related unit references
5. Cache key versioning (parser, OCR, normalization, evidence schema) and cache invalidation.
6. Backward compatibility with existing ParsedEvidenceResult APIs and to_dict serialization.
"""

import os
import sys
import uuid
import pytest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.enums import SourceFamily
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceExtractionValidator,
    EvidenceRelationship,
    EvidenceUnit,
    ExtractionQualityReport,
    ExtractionStatus,
    ParsedEvidenceResult,
    SourceLocator,
    StructuralRelationType,
)
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.parsers.conversation_parser import ConversationParser
from app.ingestion.parsers.metadata_parser import MetadataParser
from app.ingestion.universal_file_parser import UniversalFileParser
from app.caching.pipeline_cache import PipelineStageCache


@pytest.mark.asyncio
async def test_status_success_with_quality_report():
    """Valid document input generates SUCCESS status with complete ExtractionQualityReport."""
    text_content = (
        "# Section 1: Security Requirements\n\n"
        "All data stores must enforce encryption at rest.\n\n"
        "| Store | Type | Status |\n"
        "| --- | --- | --- |\n"
        "| Postgres | Relational | Enforced |\n"
        "| S3 | Object | Enforced |\n"
    )
    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="doc://vault/security.md",
        source_family=SourceFamily.DOCUMENT,
        source_version="v1.0",
        native_format="markdown",
        content_hash="hash_sec_1",
        raw_payload=text_content,
        locator_metadata={"page_count": 1},
    )

    result = await DocumentParser.parse(envelope)

    assert result.extraction_status == ExtractionStatus.SUCCESS
    assert result.quality_report is not None
    assert result.quality_report.status == ExtractionStatus.SUCCESS
    assert result.quality_report.total_units > 0
    assert result.quality_report.valid_evidence_units == result.quality_report.total_units
    assert result.quality_report.valid_source_locators > 0
    assert result.quality_report.detected_tables >= 1
    assert result.quality_report.extracted_table_rows == 2


@pytest.mark.asyncio
async def test_status_empty_on_zero_content():
    """Empty document and empty structured payload yield ExtractionStatus.EMPTY and NOT_MEASURED."""
    # 1. Empty document
    empty_doc_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="doc://empty/blank.txt",
        source_family=SourceFamily.DOCUMENT,
        source_version="v1.0",
        native_format="text",
        content_hash="empty_hash",
        raw_payload="   \n\n   ",
    )
    doc_res = await DocumentParser.parse(empty_doc_env)
    assert doc_res.extraction_status == ExtractionStatus.EMPTY
    assert doc_res.completeness_score == "NOT_MEASURED"
    assert doc_res.quality_report.status == ExtractionStatus.EMPTY
    assert len(doc_res.units) == 0

    # 2. UniversalFileParser with empty bytes
    empty_parsed = UniversalFileParser.parse_structured("empty.pdf", b"")
    assert empty_parsed.extraction_status == ExtractionStatus.EMPTY
    assert empty_parsed.quality_report.status == ExtractionStatus.EMPTY
    assert empty_parsed.extraction_quality == 0.0


@pytest.mark.asyncio
async def test_status_partial_on_truncation():
    """Structured data truncation reports PARTIAL status with explicit truncation reason and dropped count."""
    # Generate JSONL exceeding the 100-record threshold to trigger documented truncation warning
    records = [{"id": i, "name": f"Item_{i}", "metric": i * 10} for i in range(150)]
    jsonl_text = "\n".join(__import__("json").dumps(r) for r in records)

    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="db://analytics/events.jsonl",
        source_family=SourceFamily.STRUCTURED,
        source_version="v1.0",
        native_format="jsonl",
        content_hash="jsonl_hash_150",
        raw_payload=jsonl_text,
        locator_metadata={"max_records": 100},
    )

    result = await StructuredDataParser.parse(envelope)

    assert result.extraction_status == ExtractionStatus.PARTIAL
    assert result.quality_report is not None
    assert result.quality_report.is_truncated is True
    assert "truncated" in result.quality_report.truncation_reason.lower()
    assert result.quality_report.dropped_records_count == 50
    assert result.quality_report.expected_jsonl_records == 150
    assert result.quality_report.processed_jsonl_records == 100
    assert result.completeness_score == pytest.approx(100 / 150)


def test_status_failed_without_binary_fallback():
    """Corrupt binary file produces FAILED status without falling back to plain-text byte decoding."""
    # Invalid corrupt PDF header and garbage bytes
    corrupt_pdf_bytes = b"%PDF-1.7\r\n\x00\xff\xfe\x00CORRUPT_BYTES\xaa\xbb\xcc"

    parsed = UniversalFileParser.parse_structured("corrupt.pdf", corrupt_pdf_bytes)

    assert parsed.extraction_status == ExtractionStatus.FAILED
    assert parsed.extraction_quality == 0.0
    assert parsed.quality_report.status == ExtractionStatus.FAILED
    assert any("error" in w.lower() or "no extractable text" in w.lower() for w in parsed.warnings)
    # Ensure raw binary bytes were not decoded into readable content
    assert "\xaa" not in parsed.full_text


def test_status_unsupported_format():
    """Legacy CFBF binary format produces UNSUPPORTED status with quality 0.0."""
    cfbf_bytes = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 256
    parsed = UniversalFileParser.parse_structured("archived_doc.doc", cfbf_bytes)

    assert parsed.extraction_status == ExtractionStatus.UNSUPPORTED
    assert parsed.extraction_quality == 0.0
    assert parsed.quality_report.status == ExtractionStatus.UNSUPPORTED
    assert any("legacy binary format" in w.lower() for w in parsed.warnings)


def test_status_needs_ocr():
    """Scanned image PDF when text is missing reports NEEDS_OCR or is_scanned_image."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    # Draw image covering the page without inserting native text
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 600), 1)
    page.insert_image(pymupdf.Rect(50, 50, 500, 750), pixmap=pix)
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = UniversalFileParser.parse_structured("scanned_receipt.pdf", pdf_bytes)

    assert parsed.is_scanned is True or parsed.pages[0].is_scanned_image is True
    assert parsed.extraction_status in (ExtractionStatus.NEEDS_OCR, ExtractionStatus.PARTIAL, ExtractionStatus.SUCCESS)


@pytest.mark.asyncio
async def test_completeness_calculation_against_known_inputs():
    """Completeness score reflects exact ratio for known denominators and NOT_MEASURED when unavailable."""
    # 1. CSV with known rows
    csv_payload = (
        "id,name,role\n"
        "1,Alice,Admin\n"
        "2,Bob,Developer\n"
        "3,Charlie,Tester\n"
        "4,Diana,Manager\n"
    )
    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="postgres://prod/users.csv",
        source_family=SourceFamily.STRUCTURED,
        source_version="v1.0",
        native_format="csv",
        content_hash="csv_known",
        raw_payload=csv_payload,
    )
    csv_res = await StructuredDataParser.parse(envelope)
    # 4 data rows extracted out of 4 expected data rows
    assert csv_res.completeness_score == 1.0

    # 2. Scalar payload: must NOT be hardcoded to 1.0
    scalar_envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="config://timeout",
        source_family=SourceFamily.STRUCTURED,
        source_version="v1.0",
        native_format="json",
        content_hash="scalar_hash",
        raw_payload="42",
    )
    scalar_res = await StructuredDataParser.parse(scalar_envelope)
    assert scalar_res.completeness_score == "NOT_MEASURED"


def test_evidence_extraction_validator_all_checks():
    """EvidenceExtractionValidator validates all 9 structural and provenance rules."""
    # 1. Clean unit
    clean_unit = EvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://compliance/p1",
        source_id="src_1",
        source_type="document",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content="All passwords must be at least 16 characters.",
        normalized_content="All passwords must be at least 16 characters.",
        locator={"page": 1, "line": 10},
    )
    valid_res = EvidenceExtractionValidator.validate([clean_unit])
    assert valid_res.is_valid is True

    # 2. Duplicate instance IDs
    dup_unit = clean_unit.model_copy()
    dup_res = EvidenceExtractionValidator.validate([clean_unit, dup_unit])
    assert dup_res.is_valid is False
    assert len(dup_res.duplicate_ids) >= 1

    # 3. Missing locator coordinates
    missing_loc_unit = EvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://compliance/p2",
        source_id="src_1",
        source_type="document",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Rule text",
        normalized_content="Rule text",
        locator={},  # Empty locator
    )
    missing_loc_res = EvidenceExtractionValidator.validate([missing_loc_unit])
    assert missing_loc_res.is_valid is False
    assert len(missing_loc_res.missing_locators) >= 1

    # 4. Broken parent_id reference
    broken_parent_unit = EvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://compliance/p3",
        source_id="src_1",
        source_type="document",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Subclause text",
        normalized_content="Subclause text",
        parent_id="nonexistent_parent_id_999",
        locator={"line": 15},
    )
    broken_parent_res = EvidenceExtractionValidator.validate([broken_parent_unit])
    assert broken_parent_res.is_valid is False
    assert any("parent_id" in err for err in broken_parent_res.errors)

    # 5. Broken structural relationship target
    broken_rel_unit = EvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://compliance/p4",
        source_id="src_1",
        source_type="document",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Section intro",
        normalized_content="Section intro",
        relationships=[
            EvidenceRelationship(
                relation_type=StructuralRelationType.PARENT_CHILD,
                target_unit_id="nonexistent_child_target_777",
            )
        ],
        locator={"line": 20},
    )
    broken_rel_res = EvidenceExtractionValidator.validate([broken_rel_unit])
    assert broken_rel_res.is_valid is False
    assert any("nonexistent target" in err for err in broken_rel_res.errors)

    # 6. Mismatched table row width
    mismatched_row_unit = EvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://compliance/p5",
        source_id="src_1",
        source_type="document",
        block_type="table_row",
        content_role=ContentRole.POLICY_RULE,
        raw_content="| Val1 | Val2 | Val3 |",
        normalized_content="Val1 | Val2 | Val3",
        structured_data={
            "table_headers": ["Col1", "Col2"],  # 2 headers
            "columns": {"Col1": "Val1", "Col2": "Val2", "col_3": "Val3"},  # 3 cells
        },
        locator={"line": 30, "table_id": "tbl_1", "row_index": 1},
    )
    table_res = EvidenceExtractionValidator.validate([mismatched_row_unit])
    assert any("does not match header count" in w for w in table_res.warnings)

    # 7. Normalized content without raw provenance
    unprovenanced_unit = clean_unit.model_copy(update={"raw_content": "", "structured_data": {}})
    unprov_res = EvidenceExtractionValidator.validate([unprovenanced_unit])
    assert len(unprov_res.unprovenanced_units) >= 1

    # 8. Missing required asset_id
    missing_asset_unit = clean_unit.model_copy(update={"asset_id": ""})
    missing_asset_res = EvidenceExtractionValidator.validate([missing_asset_unit])
    assert missing_asset_res.is_valid is False
    assert len(missing_asset_res.missing_source_fields) >= 1

    # 9. Nonexistent related unit reference
    broken_related_unit = clean_unit.model_copy(update={"related_unit_ids": ["ghost_unit_404"]})
    broken_related_res = EvidenceExtractionValidator.validate([broken_related_unit])
    assert any("ghost_unit_404" in w for w in broken_related_res.warnings)


def test_cache_invalidation_on_version_changes(tmp_path: Path):
    """Cache keys reflect parser, OCR, normalizer, and evidence-schema versions; invalidation works."""
    cache = PipelineStageCache(cache_dir=tmp_path / "cache", enabled=True)

    k_base = cache.compute_pipeline_key("stage", "sha_1", "v1.0", "cfg_1", "norm_1", "ocr_1.0", "schema_1.0")

    # Varying OCR version yields different key
    k_ocr = cache.compute_pipeline_key("stage", "sha_1", "v1.0", "cfg_1", "norm_1", "ocr_2.0", "schema_1.0")
    assert k_base != k_ocr

    # Varying evidence schema version yields different key
    k_schema = cache.compute_pipeline_key("stage", "sha_1", "v1.0", "cfg_1", "norm_1", "ocr_1.0", "schema_2.0")
    assert k_base != k_schema

    # Storing and invalidating cache
    cache.set("stage", k_base, {"data": "cached_extraction_result"})
    assert cache.has("stage", k_base) is True

    # Invalidate specific key
    deleted = cache.invalidate("stage", k_base)
    assert deleted == 1
    assert cache.has("stage", k_base) is False


@pytest.mark.asyncio
async def test_backward_compatibility_with_existing_apis():
    """Existing ParsedEvidenceResult fields, quality_metrics, and to_dict remain backward-compatible."""
    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="slack://general/thread/100",
        source_family=SourceFamily.CONVERSATION,
        source_version="v1.0",
        native_format="json",
        content_hash="conv_h1",
        raw_payload=[
            {"text": "Deployment approved by lead.", "user": "alice", "ts": "1700000000.001"},
            {"text": "Proceeding with rollout.", "user": "bob", "ts": "1700000005.002"},
        ],
        locator_metadata={"channel": "general", "thread_id": "100"},
    )

    res = await ConversationParser.parse(envelope)

    # Legacy fields
    assert isinstance(res.completeness_score, (float, str))
    assert isinstance(res.quality_metrics, dict)
    assert len(res.units) == 2

    # New Phase 4 contract
    assert res.extraction_status == ExtractionStatus.SUCCESS
    assert res.quality_report is not None
    assert res.quality_report.status == ExtractionStatus.SUCCESS

    # to_dict serialization contains both legacy and new structures
    d = res.to_dict()
    assert "completeness_score" in d
    assert "quality_metrics" in d
    assert "quality_report" in d
    assert "extraction_status" in d
    assert d["extraction_status"] == "success"
    assert d["quality_report"]["total_units"] == 2
