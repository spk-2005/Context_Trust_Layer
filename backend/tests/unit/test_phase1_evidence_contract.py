"""
Unit tests for Phase 1: Trulin Evidence Contract and Provenance Architecture.
Verifies:
1. Deterministic identity rules (distinct occurrences for same text at different locations, shared content_hash).
2. ContentRole classification and safety (unknown roles remain UNKNOWN, never silently default to POLICY_RULE).
3. Raw content and normalized content separation without overwriting.
4. Typed SourceLocator supporting document, table, JSON, database, and message coordinates with dictionary emulation.
5. Structural relationships enforcement and strict rejection of validation relations (supports, contradicts).
6. Backward compatibility with legacy ParsedEvidenceUnit callers, properties, and dictionary unpacking.
7. Connector output preservation and canonicity/candidate separation.
"""

import uuid
import pytest

from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceRelationship,
    EvidenceUnit,
    ExtractionStatus,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
    SourceLocator,
    StructuralRelationType,
    compute_content_hash,
    compute_evidence_id,
    compute_evidence_instance_id,
)


def test_identity_rules_same_text_different_locations():
    """Same text at two distinct locations must produce distinct evidence_instance_id values and identical content_hash."""
    text = "All production database migrations must be reviewed by the Infrastructure Security Team."
    asset = "github://org/repo/infra_policy.md"
    env_id = uuid.uuid4()

    loc1 = SourceLocator(page=1, line=15, start_offset=100, end_offset=188)
    loc2 = SourceLocator(page=4, line=120, start_offset=950, end_offset=1038)

    unit1 = EvidenceUnit.create(
        envelope_id=env_id,
        asset_id=asset,
        block_type="clause",
        content_text=text,
        locator=loc1,
        sequence_index=1,
    )
    unit2 = EvidenceUnit.create(
        envelope_id=env_id,
        asset_id=asset,
        block_type="clause",
        content_text=text,
        locator=loc2,
        sequence_index=15,
    )

    # Identical content shares content_hash
    assert unit1.content_hash == unit2.content_hash
    assert len(unit1.content_hash) == 64

    # Different source coordinates produce distinct logical evidence IDs
    assert unit1.evidence_id != unit2.evidence_id
    assert unit1.evidence_id.startswith("ev_")
    assert unit2.evidence_id.startswith("ev_")

    # Different occurrences produce distinct unique occurrence IDs
    assert unit1.evidence_instance_id != unit2.evidence_instance_id
    assert unit1.evidence_instance_id.startswith("inst_")
    assert unit2.evidence_instance_id.startswith("inst_")

    # Legacy unit_id mirrors evidence_instance_id and is also distinct
    assert unit1.unit_id == unit1.evidence_instance_id
    assert unit2.unit_id == unit2.evidence_instance_id
    assert unit1.unit_id != unit2.unit_id


def test_unknown_role_does_not_become_policy_rule():
    """Unknown or invalid role strings must resolve to ContentRole.UNKNOWN, never silently defaulting to POLICY_RULE."""
    unit_invalid = EvidenceUnit.create(
        asset_id="test_doc",
        block_type="paragraph",
        content_text="Sample neutral statement without rules.",
        content_role="invalid_fabricated_role_xyz",
    )
    assert unit_invalid.content_role == ContentRole.UNKNOWN
    assert unit_invalid.content_role != ContentRole.POLICY_RULE

    unit_none = EvidenceUnit.create(
        asset_id="test_doc",
        block_type="paragraph",
        content_text="Sample neutral statement.",
        content_role=None,
    )
    assert unit_none.content_role == ContentRole.UNKNOWN

    # Direct enum assignment remains intact
    unit_explicit = EvidenceUnit.create(
        asset_id="test_doc",
        block_type="paragraph",
        content_text="A glossary definition.",
        content_role=ContentRole.DEFINITION,
    )
    assert unit_explicit.content_role == ContentRole.DEFINITION


def test_raw_content_and_normalized_content_separation():
    """Raw content must never be overwritten by normalized content or post-processing updates."""
    raw = "  \t* ALL EMPLOYEES MUST COMPLY IMMEDIATELY! \r\n"
    normalized = "All employees must comply immediately!"

    unit = EvidenceUnit.create(
        asset_id="doc1",
        block_type="clause",
        raw_content=raw,
        normalized_content=normalized,
        content_text=normalized,
    )

    assert unit.raw_content == raw
    assert unit.normalized_content == normalized
    assert unit.content_text == normalized

    # Simulate downstream normalization update
    unit.normalized_content = "All staff must comply without delay."
    unit.content_text = "All staff must comply without delay."

    # Raw content must remain completely pristine
    assert unit.raw_content == raw
    assert unit.normalized_content == "All staff must comply without delay."


def test_source_locator_typed_coordinates_and_dict_emulation():
    """SourceLocator must store document, table, JSON, database, and message coordinates and emulate a dict."""
    # 1. Document Locator
    doc_loc = SourceLocator(
        page=3,
        line=45,
        start_offset=120,
        end_offset=185,
        section_path=["Section 2", "Access Policy"],
        custom_tag="security_tier_1",
    )
    assert doc_loc.page == 3
    assert doc_loc.page_number == 3
    assert doc_loc.start_offset == 120
    assert doc_loc.start_char == 120
    assert doc_loc.end_offset == 185
    assert doc_loc.end_char == 185
    assert doc_loc.heading_path == ["Section 2", "Access Policy"]

    # Dict-like access
    assert doc_loc["page_number"] == 3
    assert doc_loc["start_char"] == 120
    assert doc_loc.get("heading_path") == ["Section 2", "Access Policy"]
    assert doc_loc["custom_tag"] == "security_tier_1"
    assert "start_char" in doc_loc
    assert "page_number" in doc_loc
    assert "custom_tag" in doc_loc

    # Kwarg unpacking
    unpacked = dict(**doc_loc)
    assert unpacked["page"] == 3
    assert unpacked["custom_tag"] == "security_tier_1"

    # 2. Table Locator
    tbl_loc = SourceLocator(
        table_id="table_line_45",
        row_index=3,
        column_index=2,
        cell_reference="C3",
    )
    assert tbl_loc.table_id == "table_line_45"
    assert tbl_loc.row_index == 3
    assert tbl_loc["cell_reference"] == "C3"

    # 3. Database Locator
    db_loc = SourceLocator(
        database_table="employees",
        primary_key="emp_9918",
        field_path="probation_period_days",
    )
    assert db_loc.database_table == "employees"
    assert db_loc["table"] == "employees"
    assert db_loc.primary_key == "emp_9918"
    assert db_loc["record_id"] == "emp_9918"
    assert db_loc.field_path == "probation_period_days"
    assert db_loc["column"] == "probation_period_days"

    # 4. Conversation / Chat Locator
    chat_loc = SourceLocator(
        thread_id="th_deploy_01",
        message_timestamp="2026-10-10T16:05:00Z",
        channel="ops-war-room",
        speaker="Lead Architect",
    )
    assert chat_loc.thread_id == "th_deploy_01"
    assert chat_loc["timestamp"] == "2026-10-10T16:05:00Z"
    assert chat_loc["channel"] == "ops-war-room"
    assert chat_loc["speaker"] == "Lead Architect"


def test_structural_relationships_and_validation_relation_rejection():
    """EvidenceRelationship must support structural relationships and strictly forbid Layer 5 validation relations."""
    # Valid structural relations
    rel1 = EvidenceRelationship(
        relation_type=StructuralRelationType.PARENT_CHILD,
        target_unit_id="unit_parent_100",
    )
    assert rel1.relation_type == StructuralRelationType.PARENT_CHILD
    assert rel1.target_unit_id == "unit_parent_100"

    rel2 = EvidenceRelationship(
        relation_type=StructuralRelationType.RECORD_HAS_FIELD,
        target_unit_id="schema_root",
    )
    assert rel2.relation_type == StructuralRelationType.RECORD_HAS_FIELD

    # Validation relations must be rejected with ValueError
    with pytest.raises(ValueError, match="forbidden in Layer 4 EvidenceUnit relationships"):
        EvidenceRelationship(
            relation_type="supports",
            target_unit_id="unit_claim_200",
        )

    with pytest.raises(ValueError, match="forbidden in Layer 4 EvidenceUnit relationships"):
        EvidenceRelationship(
            relation_type="contradicts",
            target_unit_id="unit_claim_300",
        )


def test_claim_candidacy_and_canonicity_separation():
    """Definitions, FAQ answers, examples, and exceptions must remain claim candidates even when noncanonical."""
    # Definition: non-canonical but valid claim candidate
    unit_def = EvidenceUnit.create(
        asset_id="doc_glossary",
        block_type="clause",
        content_text="Eligible Employee means any full-time salaried individual.",
        content_role=ContentRole.DEFINITION,
    )
    assert unit_def.is_canonical is False
    assert unit_def.is_claim_candidate is True
    assert unit_def.is_context_only is False

    # Example: non-canonical but valid claim candidate
    unit_ex = EvidenceUnit.create(
        asset_id="doc_policy",
        block_type="clause",
        content_text="For example, if an employee resigns on Monday, their 15-day notice ends on Tuesday two weeks later.",
        content_role=ContentRole.EXAMPLE,
    )
    assert unit_ex.is_canonical is False
    assert unit_ex.is_claim_candidate is True

    # Exception: canonical and claim candidate
    unit_exc = EvidenceUnit.create(
        asset_id="doc_policy",
        block_type="clause",
        content_text="Except where a waiver has been signed by the Managing Director, all employees must serve notice.",
        content_role=ContentRole.EXCEPTION,
    )
    assert unit_exc.is_canonical is True
    assert unit_exc.is_claim_candidate is True

    # Heading: non-canonical, not a claim candidate, context-only
    unit_hdr = EvidenceUnit.create(
        asset_id="doc_policy",
        block_type="heading",
        content_text="Section 3: Resignation and Notice Period",
    )
    assert unit_hdr.is_canonical is False
    assert unit_hdr.is_claim_candidate is False
    assert unit_hdr.is_context_only is True


def test_backward_compatibility_with_legacy_parsed_evidence_unit():
    """Existing code relying on ParsedEvidenceUnit alias and legacy fields must function identically."""
    env_id = uuid.uuid4()
    unit = ParsedEvidenceUnit.create(
        envelope_id=env_id,
        asset_id="doc_legacy",
        block_type="clause",
        content_text="Standard operative clause text.",
        locator={"line_start": 10, "line_end": 10, "start_char": 50, "end_char": 82},
        hierarchical_context=["Chapter 1", "Clause 1.1"],
        sequence_index=2,
    )

    # Legacy fields
    assert isinstance(unit, EvidenceUnit)
    assert isinstance(unit, ParsedEvidenceUnit)
    assert unit.unit_id == unit.evidence_instance_id
    assert unit.envelope_id == env_id
    assert unit.asset_id == "doc_legacy"
    assert unit.block_type == "clause"
    assert unit.content_text == "Standard operative clause text."
    assert unit.locator["start_char"] == 50
    assert unit.sequence_index == 2

    # New contract fields automatically populated
    assert unit.evidence_id.startswith("ev_")
    assert unit.evidence_instance_id.startswith("inst_")
    assert unit.raw_content == "Standard operative clause text."
    assert unit.normalized_content == "Standard operative clause text."
    assert len(unit.content_hash) == 64
    assert unit.extraction_status == ExtractionStatus.EXTRACTED
    assert unit.parser_version == "1.0.0"
    assert unit.normalization_version == "1.0.0"

    # Serializes to dictionary smoothly
    dumped = unit.model_dump()
    assert "evidence_id" in dumped
    assert "evidence_instance_id" in dumped
    assert "unit_id" in dumped
    assert "raw_content" in dumped
    assert "normalized_content" in dumped
    assert "content_text" in dumped
