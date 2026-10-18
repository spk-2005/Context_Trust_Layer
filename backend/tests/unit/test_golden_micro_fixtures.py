"""
Golden Micro-Fixtures Fast-Lane Test Suite (Pytest Marker: fast).
Executes in under 2 seconds. Provides immediate regression feedback on individual
contract covenants, table cells, headings, and normalization without parsing full PDFs.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID
import pytest

from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.models import CandidateClaim
from app.normalization.document_restructurer import DocumentSemanticRestructurer
from app.validation_gate.decision_engine import ClaimLifecycleDecisionEngine
from app.validation_gate.models import ClaimLifecycleDecision
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit

FIXTURES_DIR = Path("B:/Context_Layer_Ai/backend/tests/fixtures/golden_micro")


def _build_test_envelope(unit: ParsedEvidenceUnit) -> CanonicalSourceEnvelope:
    return EnvelopeFactory.create_from_file_upload(
        filename="micro_fixture.pdf",
        raw_bytes=unit.content_text.encode("utf-8"),
        parsed_content=unit.content_text,
        organization_id=UUID("11111111-1111-1111-1111-111111111111"),
        source_id=UUID("44444444-4444-4444-4444-444444444444"),
        document_type="policy"
    )


def _load_unit(data: dict) -> ParsedEvidenceUnit:
    u = data["input_unit"]
    return ParsedEvidenceUnit.create(
        envelope_id=UUID(u["envelope_id"]),
        asset_id="file://micro_fixture.pdf",
        block_type=u.get("block_type", "paragraph"),
        content_text=u["content_text"],
        structured_data=u.get("structured_data", {}),
        locator=u.get("locator", {}),
        hierarchical_context=u.get("hierarchical_context", [])
    )


def _ground_candidate(target: CandidateClaim, unit: ParsedEvidenceUnit, env: CanonicalSourceEnvelope) -> CandidateClaim:
    target.envelope_id = env.envelope_id
    target.asset_id = env.asset_id
    target.status = "verified"
    target.verification_plugin = "TextDocumentVerificationPlugin"
    target.verification_details = {"grounded": True, "method": "golden_micro_fixture"}
    target.source_unit_id = unit.unit_id
    target.evidence_id = f"ev:{unit.unit_id}"
    return target


@pytest.mark.fast
@pytest.mark.unit
def test_indemnity_covenant_fixture():
    """DOC005-C03: Verifies indemnity covenant extracted and approved without full agreement PDF."""
    path = FIXTURES_DIR / "contracts" / "indemnity_covenant.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    unit = _load_unit(data)
    env = _build_test_envelope(unit)

    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    target = next((c for c in claims if c.predicate == "has_indemnification_obligation"), None)
    assert target is not None, "Expected has_indemnification_obligation claim"
    assert target.subject == data["expected_candidate"]["subject"]
    assert data["expected_candidate"]["object"] in target.object

    # Ground candidate & Validation Gate check
    _ground_candidate(target, unit, env)
    evaluation = ClaimLifecycleDecisionEngine.evaluate_candidate(target, env)
    assert evaluation.lifecycle_decision == ClaimLifecycleDecision.APPROVE
    assert evaluation.composite_trust_score >= data["expected_min_trust_score"]


@pytest.mark.fast
@pytest.mark.unit
def test_interest_rate_clause_fixture():
    """DOC005-C08: Verifies interest rate covenant numeric extraction."""
    path = FIXTURES_DIR / "contracts" / "interest_rate_clause.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    unit = _load_unit(data)
    env = _build_test_envelope(unit)

    claims = DomainRuleExtractor.extract_from_unit(unit)
    target = next((c for c in claims if c.predicate == "has_interest_rate"), None)
    assert target is not None
    assert target.subject == data["expected_candidate"]["subject"]

    _ground_candidate(target, unit, env)
    evaluation = ClaimLifecycleDecisionEngine.evaluate_candidate(target, env)
    assert evaluation.lifecycle_decision == ClaimLifecycleDecision.APPROVE


@pytest.mark.fast
@pytest.mark.unit
def test_refund_matrix_row_fixture():
    """DOC009-C41: Verifies Apple Pay row is extracted and approved without ditto contamination."""
    path = FIXTURES_DIR / "policies" / "refund_matrix_row.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    unit = _load_unit(data)
    env = _build_test_envelope(unit)

    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    target = next((c for c in claims if c.subject == "Apple Pay / Google Pay" and c.predicate == "has_refund_method"), None)
    assert target is not None
    assert target.object == data["expected_candidate"]["object"]
    assert target.is_ambiguous is False

    _ground_candidate(target, unit, env)
    evaluation = ClaimLifecycleDecisionEngine.evaluate_candidate(target, env)
    assert evaluation.lifecycle_decision == ClaimLifecycleDecision.APPROVE


@pytest.mark.fast
@pytest.mark.unit
def test_inline_fused_heading_fixture():
    """DOC009 Parser: Verifies regex splitting of fused inline subsection headings."""
    path = FIXTURES_DIR / "policies" / "inline_fused_heading.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    restructured = DocumentSemanticRestructurer.normalize_headings_and_structure(data["input_text"])
    lines = restructured.splitlines()
    assert any(data["expected_heading"] in line for line in lines), "Expected heading split onto its own line"
    assert any(data["expected_body_prefix"] in line for line in lines), "Expected body prose preserved"


@pytest.mark.fast
@pytest.mark.unit
def test_photo_id_requirement_fixture():
    """DOC009-C19: Verifies photo ID requirement subject grounding via locator heading path."""
    path = FIXTURES_DIR / "policies" / "photo_id_requirement.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    unit = _load_unit(data)
    env = _build_test_envelope(unit)

    claims = DomainRuleExtractor.extract_from_unit(unit)
    target = next((c for c in claims if c.predicate == "has_identity_verification_requirement"), None)
    assert target is not None
    assert target.subject == data["expected_candidate"]["subject"]

    _ground_candidate(target, unit, env)
    evaluation = ClaimLifecycleDecisionEngine.evaluate_candidate(target, env)
    assert evaluation.lifecycle_decision == ClaimLifecycleDecision.APPROVE


@pytest.mark.fast
@pytest.mark.unit
def test_gift_receipt_rule_fixture():
    """DOC009-C48: Verifies gift receipt subject normalization and refund method mapping."""
    path = FIXTURES_DIR / "policies" / "gift_receipt_rule.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    unit = _load_unit(data)
    env = _build_test_envelope(unit)

    claims = DomainRuleExtractor.extract_from_unit(unit)
    target = next((c for c in claims if c.subject == "Gift receipt" and c.predicate == "has_refund_method"), None)
    assert target is not None
    assert "store credit" in str(target.object).lower()

    _ground_candidate(target, unit, env)
    evaluation = ClaimLifecycleDecisionEngine.evaluate_candidate(target, env)
    assert evaluation.lifecycle_decision == ClaimLifecycleDecision.APPROVE


@pytest.mark.fast
@pytest.mark.unit
def test_ambiguous_table_merged_cell_fixture():
    """Verifies that an explicitly merged cell row is flagged as ambiguous and routed to REVIEW."""
    path = FIXTURES_DIR / "policies" / "ambiguous_table_merged_cell.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    unit = _load_unit(data)
    env = _build_test_envelope(unit)

    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    assert any(c.is_ambiguous is True for c in claims)

    target = claims[0]
    _ground_candidate(target, unit, env)
    # First claim should route to REVIEW due to ambiguity
    evaluation = ClaimLifecycleDecisionEngine.evaluate_candidate(target, env)
    assert evaluation.lifecycle_decision == ClaimLifecycleDecision.REVIEW