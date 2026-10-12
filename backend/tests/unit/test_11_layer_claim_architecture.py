"""Unit tests for the 11-Stage Recommended Claim-Extraction Architecture.

Covers:
1. Table-aware extraction with row, cell, column binding and condition isolation
   (e.g., Level C Middle Management -> 60 days for confirmed, 15 days for probationers).
2. Detection of ambiguous/merged cells and structural table anomalies routing to REVIEW.
3. 6-State CoverageLedger ensuring 100% accounting and zero unaccounted omissions.
4. Orthogonal trust dimensions: Authority cannot override structural ambiguity or missing evidence.
"""

import uuid
import pytest
from app.ingestion.envelope import CanonicalSourceEnvelope, SourceFamily, SourceIntent, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.extraction.models import (
    CandidateClaim,
    UnitOutcome,
    ExtractionStrategyType,
    Layer5ExtractionResult,
)
from app.extraction.completeness_ledger import CompletenessLedger
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.pipeline import global_extraction_pipeline
from app.validation_gate.models import (
    CandidateGateEvaluation,
    DimensionEvaluation,
    CompletenessStatus,
    SourceMatchStatus,
    MeaningStatus,
    ScopeStatus,
    TimeStatus,
    AuthorityStatus,
    ReviewStatus,
)
from app.validation_gate.evaluators import CompletenessEvaluator, MeaningEvaluator
from app.validation_gate.decision_engine import ClaimLifecycleDecisionEngine, ClaimLifecycleDecision


@pytest.fixture
def org_and_source():
    return uuid.uuid4(), uuid.uuid4()


@pytest.mark.asyncio
async def test_table_aware_notice_period_extraction(org_and_source):
    """Test extracting exact notice period table with row, cell, condition binding."""
    org_id, src_id = org_and_source
    table_content = """# Employment Notice Period Policy
The following table outlines notice period requirements across management levels.

| Level | Group | Confirmed Notice Period | Probationers Notice Period |
| Level A | Senior Leadership | 90 days | 30 days |
| Level B | Senior Management | 90 days | 30 days |
| Level C | Middle Management | 60 days | 15 days |
| Level D | Frontline Operations | 30 days | 15 days |
"""
    envelope = EnvelopeFactory.create_from_file_upload(
        filename="notice_policy.md",
        raw_bytes=table_content.encode("utf-8"),
        parsed_content=table_content,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    # Layer 4: Parsing
    evidence = await DocumentParser.parse(envelope)
    table_units = [u for u in evidence.units if u.block_type == "table_row"]
    assert len(table_units) == 4, f"Expected 4 table rows, got {len(table_units)}"

    # Find Level C row
    level_c_unit = next(u for u in table_units if "Level C" in u.content_text)
    assert level_c_unit.structured_data is not None
    cols = level_c_unit.structured_data.get("columns", {})
    assert cols.get("Level") == "Level C"
    assert cols.get("Group") == "Middle Management"

    # Layer 5: Table-Aware Extraction
    claims = DeterministicSchemaExtractor.extract_from_unit(level_c_unit)
    assert len(claims) >= 2, f"Expected at least 2 claims (confirmed & probationers), got {len(claims)}"

    # Check confirmed notice period claim
    confirmed_claim = next((c for c in claims if "60" in str(c.object) or "60" in str(c.value)), None)
    assert confirmed_claim is not None, "Confirmed notice period claim not found"
    assert confirmed_claim.value == 60.0
    assert confirmed_claim.unit == "days"
    assert "Confirmed status" in confirmed_claim.conditions
    assert "Level C" in confirmed_claim.subject
    assert "Middle Management" in confirmed_claim.subject
    assert confirmed_claim.scope.get("Level") == "Level C"
    assert confirmed_claim.scope.get("Group") == "Middle Management"
    assert not confirmed_claim.is_ambiguous

    # Check probationers notice period claim
    probation_claim = next((c for c in claims if "15" in str(c.object) or "15" in str(c.value)), None)
    assert probation_claim is not None, "Probationers notice period claim not found"
    assert probation_claim.value == 15.0
    assert probation_claim.unit == "days"
    assert "Probationary status" in probation_claim.conditions
    assert not probation_claim.is_ambiguous


@pytest.mark.asyncio
async def test_ambiguous_table_merged_cells_flagged_and_reviewed(org_and_source):
    """Test that ambiguous merged cells or column mismatches are flagged and routed to REVIEW."""
    org_id, src_id = org_and_source
    ambiguous_table = """# Organization Hierarchy Matrix
| Department | Grade | Notice Window |
| Engineering | Staff | 60 days |
| Product | [Merged with above] | 45 days |
"""
    envelope = EnvelopeFactory.create_from_file_upload(
        filename="hierarchy.md",
        raw_bytes=ambiguous_table.encode("utf-8"),
        parsed_content=ambiguous_table,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    evidence = await DocumentParser.parse(envelope)
    table_units = [u for u in evidence.units if u.block_type == "table_row"]
    assert len(table_units) == 2

    # Second row contains '[Merged with above]'
    merged_unit = table_units[1]
    assert merged_unit.structured_data.get("is_ambiguous") is True
    assert "merged or spanned" in merged_unit.structured_data.get("ambiguity_reason", "")

    # Extraction must mark the candidate claim as ambiguous
    claims = DeterministicSchemaExtractor.extract_from_unit(merged_unit)
    assert len(claims) > 0
    candidate = claims[0]
    assert candidate.is_ambiguous is True
    assert candidate.ambiguity_reason is not None

    # Completeness evaluator must fail full approval for ambiguous claim
    comp_eval = CompletenessEvaluator.evaluate(candidate)
    assert comp_eval.status == CompletenessStatus.PARTIAL
    assert comp_eval.passed is False
    assert comp_eval.score <= 0.75

    # Mark candidate verified by evidence plugin to isolate ambiguity and completeness review
    candidate.status = "verified"
    candidate.verification_plugin = "DeterministicTablePlugin"

    # Decision engine must route to REVIEW even if source authority is 100%
    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(
        candidate=candidate,
        envelope=envelope,
    )
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW, "Ambiguous claim must require human review"
    assert gate_eval.review_trigger.status == ReviewStatus.REVIEW_REQUIRED.value
    assert gate_eval.completeness.passed is False
    assert gate_eval.is_ambiguous is True


def test_coverage_ledger_six_states_accounting():
    """Test 6-state CoverageLedger guaranteeing 100% unit accounting."""
    ledger = CompletenessLedger(envelope_id=uuid.uuid4(), asset_id="doc1")

    ledger.record_entry("u1", "clause", "verified", "rule", "PluginA", True, 2, UnitOutcome.PROCESSED_WITH_CLAIMS)
    ledger.record_entry("u2", "section_heading", "verified", "rule", "PluginA", True, 0, UnitOutcome.PROCESSED_NO_CLAIMS)
    ledger.record_entry("u3", "whitespace", "skipped", "rule", "PluginA", False, 0, UnitOutcome.SKIPPED_WITH_REASON)
    ledger.record_entry("u4", "table_row", "unverified", "rule", "PluginA", False, 1, UnitOutcome.NEEDS_REVIEW)
    ledger.record_entry("u5", "network_call", "failed", "rule", "PluginA", False, 0, UnitOutcome.FAILED_RETRYABLE)
    ledger.record_entry("u6", "corrupt_data", "failed", "rule", "PluginA", False, 0, UnitOutcome.FAILED_TERMINAL)

    summary = ledger.get_summary()
    assert summary["total_units"] == 6
    assert summary["unaccounted_omissions"] == 0
    assert summary["accounting_completeness"] == 1.0

    breakdown = summary["breakdown"]
    assert breakdown["processed_with_claims"] == 1
    assert breakdown["processed_no_claims"] == 1
    assert breakdown["skipped_with_reason"] == 1
    assert breakdown["needs_review"] == 1
    assert breakdown["failed_retryable"] == 1
    assert breakdown["failed_terminal"] == 1


@pytest.mark.asyncio
async def test_end_to_end_11_layer_pipeline_execution(org_and_source):
    """End-to-end execution of global extraction pipeline on multi-section document."""
    org_id, src_id = org_and_source
    doc_content = """# Standard Operating Procedure 2026
## Overview
This document defines operational guidelines for customer support.

| Level | Group | Confirmed Notice Period | Probationers Notice Period |
| Level C | Middle Management | 60 days | 15 days |

Staff members must log all tickets in the Enterprise Portal within 2 hours.
"""
    envelope = EnvelopeFactory.create_from_file_upload(
        filename="sop.md",
        raw_bytes=doc_content.encode("utf-8"),
        parsed_content=doc_content,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    evidence = await DocumentParser.parse(envelope)
    l5_result = await global_extraction_pipeline.process_envelope(envelope, evidence)

    assert l5_result.claims_extracted > 0
    ledger_summary = l5_result.ledger_summary
    assert ledger_summary["accounting_completeness"] == 1.0
    assert ledger_summary["unaccounted_omissions"] == 0

    # Verify that table claims extracted have condition and numeric value
    table_claims = [c for c in l5_result.candidates if c.extraction_strategy == ExtractionStrategyType.TABLE_AWARE]
    assert len(table_claims) >= 2
    c60 = next((c for c in table_claims if c.value == 60.0), None)
    assert c60 is not None
    assert c60.unit == "days"
    assert "Confirmed status" in c60.conditions
