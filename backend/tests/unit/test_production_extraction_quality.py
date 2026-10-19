import uuid
import pytest
from app.extraction.models import CandidateClaim, TableGridBinding
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit
from app.validation_gate.evaluators import CompletenessEvaluator


@pytest.mark.asyncio
async def test_trailhead_box_multiline_stitching_and_entity_binding():
    """
    Test 1: Trailhead Box Multiline Row Stitching & Entity Binding.
    Verifies:
    - Continuation line with empty col 0 is stitched into preceding row.
    - Zero claims with subject 'Governed Entity'.
    - 3 discrete claims for Trailhead Box subscription:
      1. has_billing_schedule: Monthly, 1st of month
      2. has_cancellation_rule: Anytime before the 25th
      3. has_refund_rule: Full refund if cancelled within 48 hours of renewal and box not shipped
    """
    markdown_content = """# Northwind Subscriptions

## 9. Subscription Services
| Service | Billing Schedule | Cancellation | Refund Rule |
|---|---|---|---|
| Trailhead Box | Monthly, 1st of | Anytime before the | Full refund if cancelled within 48 hours |
| | month | 25th | of renewal and box not shipped |
"""

    env = EnvelopeFactory.create_from_file_upload(
        filename="northwind_subs.md",
        raw_bytes=markdown_content.encode("utf-8"),
        parsed_content=markdown_content,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )

    parsed = await DocumentParser.parse(env)
    # The two markdown lines should be stitched into exactly 1 table_row unit
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    assert len(table_units) == 1, f"Expected 1 stitched row, got {len(table_units)}"

    claims = DeterministicSchemaExtractor.extract_from_unit(table_units[0])
    assert len(claims) == 3

    # Verify no 'Governed Entity' subjects
    for c in claims:
        assert c.subject.lower() != "governed entity"
        assert "Trailhead Box" in c.subject
        assert "subscription" in c.subject.lower()

    # 1. Billing Schedule
    billing_claim = next(c for c in claims if c.predicate == "has_billing_schedule")
    assert "Monthly, 1st of month" in billing_claim.object

    # 2. Cancellation Rule
    cancel_claim = next(c for c in claims if c.predicate == "has_cancellation_rule")
    assert "Anytime before the 25th" in cancel_claim.object

    # 3. Refund Rule
    refund_claim = next(c for c in claims if c.predicate == "has_refund_rule")
    assert "Full refund if cancelled within 48 hours of renewal and box not shipped" in refund_claim.object


@pytest.mark.asyncio
async def test_warranty_resolution_path_and_holiday_deadline():
    """
    Test 2: Defective Items Warranty Routing & Holiday Deadline.
    Verifies:
    - Defective items -> has_resolution_path = 'warranty_claim' with cross_reference to Section 14.
    - Holiday purchases -> has_return_deadline with calendar_date unit.
    """
    markdown_content = """# Northwind Return Windows

## 3. Return Windows
| Item Category | Return Window |
|---|---|
| Defective items | Covered by warranty - see Section 14 |
| Holiday purchases (Nov 1 - Dec 24) | Until January 31 of the following year |
"""

    env = EnvelopeFactory.create_from_file_upload(
        filename="return_windows.md",
        raw_bytes=markdown_content.encode("utf-8"),
        parsed_content=markdown_content,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )

    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    assert len(table_units) == 2

    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    # Warranty routing
    defective_claim = next(c for c in claims if "Defective" in c.subject)
    assert defective_claim.predicate == "has_resolution_path"
    assert defective_claim.value == "warranty_claim"
    assert "Section 14" in defective_claim.cross_references
    # Must NOT extract numeric 14 as duration
    assert defective_claim.unit != "days"

    # Holiday deadline
    holiday_claim = next(c for c in claims if "Holiday" in c.subject)
    assert holiday_claim.predicate == "has_return_deadline"
    assert holiday_claim.unit == "calendar_date"
    assert "holiday_purchase_window" in holiday_claim.qualifiers


@pytest.mark.asyncio
async def test_form_field_specification_isolation():
    """
    Test 3: Form Field Specification Isolation.
    Verifies:
    - Tables with Field Name, Required, Example are classified as form_field_specification.
    - Claims are tagged with ContentRole.PROCEDURE and is_canonical = False.
    - Predicates are is_required_for_refund_request and has_example_value.
    """
    markdown_content = """# RMA Submission Requirements

## 5. Return Request Form
| Field Name | Required? | Example / Format |
|---|---|---|
| Order number | Yes | NW-10482391 |
| Photos | If damaged | photo.jpg |
"""

    env = EnvelopeFactory.create_from_file_upload(
        filename="rma_form.md",
        raw_bytes=markdown_content.encode("utf-8"),
        parsed_content=markdown_content,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="procedure",
    )

    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    assert len(table_units) == 2

    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    assert len(claims) == 4
    for c in claims:
        assert c.claim_type == "form_field_specification"
        assert c.content_role == ContentRole.PROCEDURE
        assert c.is_canonical is False

    order_req = next(c for c in claims if "Order number" in c.subject and c.predicate == "is_required_for_refund_request")
    assert order_req.object == "Yes"

    order_ex = next(c for c in claims if "Order number" in c.subject and c.predicate == "has_example_value")
    assert order_ex.object == "NW-10482391"


@pytest.mark.asyncio
async def test_canonical_domain_predicates_and_qualifiers():
    """
    Test 4: Canonical Domain Predicates & Qualifiers.
    Verifies:
    - Partial refund percentages -> has_refund_percentage with range 50-75%.
    - Payment timelines -> has_posting_duration with qualifier 'up_to'.
    - Stage durations -> has_stage_duration.
    """
    markdown_content = """# Northwind Policies

## 4. Refund Percentages
| Item Condition | Refund Percentage |
|---|---|
| Light wear or signs of use | 50% - 75% |
| Damaged by customer | Not eligible |

## 8. Payment Methods
| Payment Method | Notes / Posting Time |
|---|---|
| Debit card | Up to 10 business days |

## 7. Processing Stages
| Stage | Duration |
|---|---|
| Warehouse inspection | 1-2 business days |
"""

    env = EnvelopeFactory.create_from_file_upload(
        filename="nw_policies.md",
        raw_bytes=markdown_content.encode("utf-8"),
        parsed_content=markdown_content,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )

    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    # Refund percentage
    light_wear_claim = next(c for c in claims if "Light wear" in c.subject)
    assert light_wear_claim.predicate == "has_refund_percentage"
    assert light_wear_claim.value == "50-75"
    assert light_wear_claim.unit == "%"

    # Ineligible
    damaged_claim = next(c for c in claims if "Damaged" in c.subject or "Damaged" in str(c.conditions) or "Damaged" in c.claim_text or c.predicate == "has_refund_eligibility")
    assert damaged_claim.predicate == "has_refund_eligibility"
    assert damaged_claim.object.lower() == "not eligible"

    # Posting duration
    debit_claim = next(c for c in claims if "Debit card" in c.subject)
    assert debit_claim.predicate == "has_posting_duration"
    assert debit_claim.value == 10
    assert "up_to" in debit_claim.qualifiers

    # Stage duration
    stage_claim = next(c for c in claims if "Warehouse inspection" in c.subject)
    assert stage_claim.predicate == "has_stage_duration"


def test_validation_gate_rejects_governed_entity_and_orphan_fragments():
    """
    Test 5: CompletenessEvaluator rejects Governed Entity and split orphan fragments.
    """
    # 1. Governed Entity rejection
    bad_cand = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit_1",
        asset_id="doc.md",
        claim_text="Governed Entity specifies Billing as month.",
        subject="Governed Entity",
        predicate="has_billing_schedule",
        object_="month",
        evidence_text_span="Governed Entity specifies Billing as month.",
    )
    eval_res = CompletenessEvaluator.evaluate(bad_cand)
    assert eval_res.passed is False
    assert "Generic fallback subject" in eval_res.reason

    # 2. Orphan cell fragment rejection
    fragment_cand = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="unit_2",
        asset_id="doc.md",
        claim_text="Trailhead Box specifies Cancellation as 25th.",
        subject="Trailhead Box subscription",
        predicate="has_cancellation_rule",
        object_="25th",
        evidence_text_span="Trailhead Box | 25th",
    )
    eval_res2 = CompletenessEvaluator.evaluate(fragment_cand)
    assert eval_res2.passed is False
    assert "orphan cell fragment" in eval_res2.reason
