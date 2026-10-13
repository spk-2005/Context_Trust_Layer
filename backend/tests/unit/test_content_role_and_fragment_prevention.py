"""
Unit tests for Content Role Classification, Structural Provenance,
Anti-Fragment Gates, and Policy-Eligible Conflict Isolation.

Verifies:
1. Preserve structure before normalizing (page, section, table ID, row/col, headings, locator).
2. Classify content role (POLICY_RULE, DEFINITION, PROCEDURE, FAQ, EXAMPLE, REVISION_HISTORY, HEADING, CONTACT_INFO).
3. Do not approve fragments (complete assertion & condition retention).
4. Extract tables as tables (row entity, column meaning, value, unit, qualifiers, section context).
5. Keep examples and history non-canonical (is_canonical=False).
6. Only send policy-eligible claims to conflict detection (bypass headings, FAQs, examples, definitions, history).
"""

import uuid
import pytest
from app.db.enums import SourceIntent
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit
from app.extraction.models import (
    CandidateClaim,
    ExtractionStrategyType,
    TableGridBinding,
)
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.validation_gate import (
    ClaimLifecycleDecision,
    ClaimLifecycleDecisionEngine,
    CompletenessEvaluator,
    DecisionCode,
)
from app.conflict_engine.detector import ConflictDetector


@pytest.fixture
def test_envelope():
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()
    text = """# Employees Notice Period Policy

## 1. Definitions
For the purposes of this policy, 'Probationer' means an employee who has not yet completed the initial probationary evaluation period.

## 2. Contact Information
For any clarifications regarding notice periods, please contact people_success@company.com or call +1-800-555-0199.

## 3. Frequently Asked Questions
Q: Can an employee take annual leave during the notice period?
A: No, leave cannot be availed during notice period unless specifically authorized by the Department Head.

## 4. Operational Procedure
Step 1: The employee must submit resignation via the HR Portal.
Step 2: Manager schedules an exit interview within 3 business days.

## 5. Illustrative Scenarios
For example, if an employee in Grade B resigns on May 1st during probation, the required notice duration is exactly 15 days.

## 6. Notice Duration Matrix
| Level & Grade | Group Category | Confirmed Notice Duration | Probationers |
| A (A1 & A2) | CXO | 90 Days | 15 days |
| C (C1, C2 & C3) | Middle Management | 60 Days | 15 days |

## 7. Revision History
| Version | Date | Description | Author |
| 1.0 | 2021-01-01 | Initial Policy Baseline | HR Team |
"""
    return EnvelopeFactory.create_from_file_upload(
        filename="notice_policy.md",
        raw_bytes=text.encode("utf-8"),
        parsed_content=text,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )


@pytest.mark.asyncio
async def test_content_role_classification_and_structural_provenance(test_envelope):
    """Verifies that evidence units receive rich structural provenance and explicit ContentRole tags."""
    evidence_res = await DocumentParser.parse(test_envelope)
    units = evidence_res.units

    roles = {u.content_role for u in units}
    assert ContentRole.HEADING in roles
    assert ContentRole.DEFINITION in roles
    assert ContentRole.CONTACT_INFO in roles
    assert ContentRole.FAQ in roles
    assert ContentRole.PROCEDURE in roles
    assert ContentRole.EXAMPLE in roles
    assert ContentRole.POLICY_RULE in roles
    assert ContentRole.REVISION_HISTORY in roles

    # Verify structural provenance on units
    for u in units:
        loc = u.locator
        assert "start_char" in loc
        assert "end_char" in loc
        assert "line_start" in loc
        assert "line_end" in loc
        if u.block_type == "table_row":
            assert "table_id" in loc or "table_start_line" in loc
            assert "row_index" in loc or "row_line" in loc


@pytest.mark.asyncio
async def test_extract_tables_as_tables_with_grid_fidelity(test_envelope):
    """Verifies table rows preserve row entity, column meaning, scalar, unit, qualifiers, and section context."""
    evidence_res = await DocumentParser.parse(test_envelope)
    
    # Filter for policy matrix units
    matrix_units = [u for u in evidence_res.units if u.content_role == ContentRole.POLICY_RULE and u.block_type == "table_row"]
    assert len(matrix_units) >= 2

    # Extract claims via DeterministicSchemaExtractor
    claims = []
    for u in matrix_units:
        extracted = DeterministicSchemaExtractor.extract_from_unit(u)
        claims.extend(extracted)

    assert len(claims) >= 4  # 2 rows x 2 columns (Confirmed + Probationers)
    for c in claims:
        # Check TableGridBinding
        assert c.table_binding is not None
        assert c.table_binding.table_id != ""
        assert c.table_binding.row_key != ""
        assert c.table_binding.column_header != ""
        assert c.value is not None
        assert c.unit == "days"
        
        # Section context inherited
        assert len(c.locator.get("heading_path", [])) > 0 or len(c.structured_values.get("section_context", [])) > 0


@pytest.mark.asyncio
async def test_anti_fragment_gate_rejects_incomplete_assertions(test_envelope):
    """Verifies that fragments lacking subject, predicate, object, or required conditions are rejected."""
    # 1. Fragment with missing subject
    f1 = CandidateClaim.create(
        envelope_id=test_envelope.envelope_id,
        unit_id="u1",
        asset_id=test_envelope.asset_id,
        claim_text="requires 15 days",
        subject="",  # Missing subject
        predicate="requires",
        object_="15 days",
        evidence_text_span="requires 15 days",
        conditions=[],
    )
    eval1 = CompletenessEvaluator.evaluate(f1)
    assert not eval1.passed
    assert "missing mandatory attributes" in eval1.reason.lower()

    # 2. Fragment with ungrounded pronoun subject ("It")
    f2 = CandidateClaim.create(
        envelope_id=test_envelope.envelope_id,
        unit_id="u2",
        asset_id=test_envelope.asset_id,
        claim_text="It outlines 30 days notice.",
        subject="It",  # Pronoun fragment
        predicate="outlines_notice",
        object_="30 days",
        evidence_text_span="It outlines 30 days notice.",
        conditions=[],
    )
    eval2 = CompletenessEvaluator.evaluate(f2)
    assert not eval2.passed
    assert "pronoun" in eval2.reason.lower() or "fragment" in eval2.reason.lower()

    # Check Knockout Decision in DecisionEngine
    lifecycle_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(f2, test_envelope)
    assert lifecycle_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert lifecycle_eval.decision_code == DecisionCode.FRAGMENT_ASSERTION_DISCARDED


@pytest.mark.asyncio
async def test_examples_and_history_flagged_non_canonical(test_envelope):
    """Verifies that units classified as EXAMPLE or REVISION_HISTORY produce is_canonical=False claims."""
    evidence_res = await DocumentParser.parse(test_envelope)
    example_units = [u for u in evidence_res.units if u.content_role in (ContentRole.EXAMPLE, ContentRole.REVISION_HISTORY)]
    assert len(example_units) >= 1

    for u in example_units:
        assert u.content_role in (ContentRole.EXAMPLE, ContentRole.REVISION_HISTORY)
        # When converted or extracted, canonicity is False
        assert not u.is_canonical


@pytest.mark.asyncio
async def test_only_policy_eligible_claims_enter_conflict_detection():
    """Verifies that headings, FAQs, definitions, examples, and history are bypassed from conflict evaluation."""
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    detector = ConflictDetector(mock_session)

    # A heading or example claim
    example_claim = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u_ex",
        asset_id="policy.md",
        claim_text="For example, John had a 15 day notice period in 2019.",
        subject="John (Example)",
        predicate="has_notice_period",
        object_="15 days",
        evidence_text_span="For example, John had a 15 day notice period in 2019.",
        is_canonical=False,
    )
    example_claim.content_role = ContentRole.EXAMPLE

    conflicts = await detector.detect_conflicts_for_claim(example_claim)
    assert len(conflicts) == 0  # Bypassed immediately with 0 queries/calls
