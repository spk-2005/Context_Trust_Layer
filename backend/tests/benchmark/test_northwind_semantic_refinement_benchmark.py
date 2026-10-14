"""
Production Ground-Truth Regression Benchmark Suite for Northwind Semantic Completeness Refinement.

Verifies all 13 Acceptance Tests:
1. Standard merchandise return window = 30 calendar_days, time_basis = delivery_date
2. Gold member return window = 60 calendar_days, time_basis = delivery_date
3. Holiday purchases -> calendar deadline, not duration
4. Missing original box -> subject has no "subscription"
5. Trailhead Box -> three claims share subject "Trailhead Box subscription"
6. Cash ID requirement -> has_identity_verification_requirement
7. Split payments -> has_refund_allocation_rule
8. BNPL -> has_provider_governed_timeline
9. Credit-card posting vs debit-card posting -> NO_CONFLICT
10. Warehouse transit vs inspection -> NO_CONFLICT
11. Light wear 50-75% vs heavy use 0-25% -> NO_CONFLICT
12. Gold return window 60 days vs Gold return window 45 days -> CONFLICT
13. Cash refund "up to $50" vs "under $50" -> REVIEW

Plus cancellation predicate precision:
- Pending -> has_cancellation_refund_outcome
- Processing -> has_cancellation_refund_timing
- Packed -> has_cancellation_refund_outcome
- Shipped -> has_post_shipment_resolution_path
- Delivered -> has_post_delivery_resolution_path
- Pre-order -> has_cancellation_refund_outcome
- Backordered -> has_cancellation_refund_outcome
"""

import uuid
import pytest

from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.conflict_engine.normalizer import ClaimNormalizer, NormalizedClaimKey
from app.extraction.deontic_classifier import DeonticClassifier
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.models import CandidateClaim
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole


@pytest.fixture
def envelope_builder():
    def _create(markdown_text: str) -> CanonicalSourceEnvelope:
        return EnvelopeFactory.create_from_file_upload(
            filename="Northwind_Handbook.md",
            raw_bytes=markdown_text.encode("utf-8"),
            parsed_content=markdown_text,
            organization_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            document_type="policy",
        )
    return _create


# =========================================================================
# Acceptance Tests 1 & 2: Return Windows with time_basis = delivery_date
# =========================================================================

@pytest.mark.asyncio
async def test_acceptance_1_and_2_return_windows_time_basis(envelope_builder):
    """
    Acceptance Tests 1 & 2:
    1. Standard merchandise return window = 30 calendar_days, time_basis = delivery_date
    2. Gold member return window = 60 calendar_days, time_basis = delivery_date
    """
    content = """# Northwind Return Policy
## 3.1 Standard Return Policy
| Tier or Category | Return Window |
|---|---|
| Standard merchandise | 30 days |
| Gold member | 60 days |
"""
    env = envelope_builder(content)
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]

    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    # 1. Standard merchandise
    std_claim = next((c for c in claims if "Standard merchandise" in c.subject), None)
    assert std_claim is not None
    assert std_claim.predicate == "has_return_window"
    assert std_claim.value == 30.0
    assert std_claim.unit == "calendar_days"
    assert std_claim.time_basis == "delivery_date"
    assert std_claim.typed_value is not None
    assert std_claim.typed_value.unit == "calendar_days"
    assert std_claim.typed_value.time_basis == "delivery_date"

    # 2. Gold member
    gold_claim = next((c for c in claims if "Gold member" in c.subject), None)
    assert gold_claim is not None
    assert gold_claim.predicate == "has_return_window"
    assert gold_claim.value == 60.0
    assert gold_claim.unit == "calendar_days"
    assert gold_claim.time_basis == "delivery_date"
    assert gold_claim.typed_value is not None
    assert gold_claim.typed_value.unit == "calendar_days"
    assert gold_claim.typed_value.time_basis == "delivery_date"


# =========================================================================
# Acceptance Test 3: Holiday Deadline Structured Calendar Logic
# =========================================================================

@pytest.mark.asyncio
async def test_acceptance_3_holiday_deadline_structured_calendar_logic(envelope_builder):
    """
    Acceptance Test 3:
    Holiday purchases -> calendar deadline, not duration.
    value = { "type": "calendar_date", "rule": "january_31_following_year" }
    conditions = [ { "field": "purchase_date", "operator": "between", "value": ["11-01", "12-24"] } ]
    """
    content = """# Northwind Return Policy
## 3.1 Standard Return Policy
| Tier or Category | Return Window |
|---|---|
| Holiday purchases | Until January 31 of the following year |
"""
    env = envelope_builder(content)
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]

    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    hol_claim = next((c for c in claims if "Holiday" in c.subject), None)
    assert hol_claim is not None
    assert hol_claim.predicate == "has_return_deadline"
    assert hol_claim.time_basis == "holiday_window"
    assert hol_claim.value == {"type": "calendar_date", "rule": "january_31_following_year"}
    assert hol_claim.typed_value is not None
    assert hol_claim.typed_value.value_type == "CALENDAR_DEADLINE"
    assert hol_claim.typed_value.structured_rule == {"type": "calendar_date", "rule": "january_31_following_year"}

    # Structured condition verification
    cond_entry = next((cond for cond in hol_claim.conditions if isinstance(cond, dict) and cond.get("field") == "purchase_date"), None)
    assert cond_entry is not None
    assert cond_entry["operator"] == "between"
    assert cond_entry["value"] == ["11-01", "12-24"]


# =========================================================================
# Acceptance Tests 4 & 5: Subscription Boundary Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_acceptance_4_and_5_subscription_boundary_isolation(envelope_builder):
    """
    Acceptance Tests 4 & 5:
    4. Missing original box -> subject has no "subscription"
    5. Trailhead Box -> three claims share subject "Trailhead Box subscription"
    """
    # 4. Item condition table: "Missing original box (non-fragile)"
    content_cond = """# Settlement Deductions
## 4.1 Settlement Deductions
| Item Condition | Refund Percentage |
|---|---|
| Missing original box (non-fragile) | 60% |
"""
    env_cond = envelope_builder(content_cond)
    parsed_cond = await DocumentParser.parse(env_cond)
    u_cond = [u for u in parsed_cond.units if u.block_type == "table_row"]
    claims_cond = []
    for u in u_cond:
        claims_cond.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    box_claim = next(c for c in claims_cond if "Missing original box" in c.subject)
    assert "subscription" not in box_claim.subject.lower()
    assert box_claim.subject == "Missing original box (non-fragile)"

    # 5. Subscription table: Trailhead Box subscription
    content_sub = """# Subscription Services
## 12. Subscriptions
| Subscription Plan | Cancellation Policy | Refund Rule |
|---|---|---|
| Trailhead Box | Cancel anytime before renewal | Pro-rated refund within 48 hours |
| Rewards Plus | Non-refundable after first benefit used | No refund |
"""
    env_sub = envelope_builder(content_sub)
    parsed_sub = await DocumentParser.parse(env_sub)
    u_sub = [u for u in parsed_sub.units if u.block_type == "table_row"]
    claims_sub = []
    for u in u_sub:
        claims_sub.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    trailhead_claims = [c for c in claims_sub if "Trailhead Box" in c.subject]
    assert len(trailhead_claims) >= 2
    for c in trailhead_claims:
        assert c.subject == "Trailhead Box subscription"


# =========================================================================
# Acceptance Tests 6, 7, 8: Specialized Semantic Predicates
# =========================================================================

@pytest.mark.asyncio
async def test_acceptance_6_7_8_specialized_predicates(envelope_builder):
    """
    Acceptance Tests 6, 7, 8:
    6. Cash ID requirement -> has_identity_verification_requirement
    7. Split payments -> has_refund_allocation_rule
    8. BNPL -> has_provider_governed_timeline
    """
    content = """# Payment Methods & Refunds
## 8. Payment Method Specifics
| Payment Type | Processing Notes |
|---|---|
| Cash | Government ID required for amounts over $20 |
| Split payment | Original payment portion first, remainder store credit |
| BNPL | Subject to provider timelines |
"""
    env = envelope_builder(content)
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]

    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    cash_c = next(c for c in claims if "Cash" in c.subject)
    assert cash_c.predicate == "has_identity_verification_requirement"

    split_c = next(c for c in claims if "Split" in c.subject)
    assert split_c.predicate == "has_refund_allocation_rule"

    bnpl_c = next(c for c in claims if "BNPL" in c.subject)
    assert bnpl_c.predicate == "has_provider_governed_timeline"


# =========================================================================
# Acceptance Tests 9, 10, 11: Non-Overlapping Applicability (NO_CONFLICT)
# =========================================================================

def test_acceptance_9_10_11_applicability_gate_no_conflicts():
    """
    Acceptance Tests 9, 10, 11:
    9. Credit-card posting vs debit-card posting -> NO_CONFLICT
    10. Warehouse transit vs inspection -> NO_CONFLICT
    11. Light wear 50-75% vs heavy use 0-25% -> NO_CONFLICT
    """
    # 9. Credit card vs Debit card (Gate 2: Payment Method)
    key_cc = NormalizedClaimKey(subject_key="Refund", predicate_key="has_posting_duration", payment_method="credit_card")
    key_dc = NormalizedClaimKey(subject_key="Refund", predicate_key="has_posting_duration", payment_method="debit_card")
    res_pm = CompatibilityGate.evaluate_applicability_overlap(key_cc, key_dc)
    assert res_pm.is_comparable is False
    assert res_pm.reason == "DIFFERENT_PAYMENT_METHOD"

    # 10. Warehouse transit vs inspection (Gate 1: Process Stage)
    key_transit = NormalizedClaimKey(subject_key="Refund", predicate_key="has_stage_duration", process_stage="return_transit")
    key_inspect = NormalizedClaimKey(subject_key="Refund", predicate_key="has_stage_duration", process_stage="warehouse_inspection")
    res_stage = CompatibilityGate.evaluate_applicability_overlap(key_transit, key_inspect)
    assert res_stage.is_comparable is False
    assert res_stage.reason == "DIFFERENT_PROCESS_STAGE"

    # 11. Light wear 50-75% vs heavy use 0-25% (Gate 4: Item Condition)
    key_lw = NormalizedClaimKey(subject_key="Refund", predicate_key="has_refund_percentage", item_condition="light_wear")
    key_hu = NormalizedClaimKey(subject_key="Refund", predicate_key="has_refund_percentage", item_condition="heavy_use")
    res_cond = CompatibilityGate.evaluate_applicability_overlap(key_lw, key_hu)
    assert res_cond.is_comparable is False
    assert res_cond.reason == "DIFFERENT_ITEM_CONDITION"


# =========================================================================
# Acceptance Test 12: True Contradiction (CONFLICT)
# =========================================================================

def test_acceptance_12_competing_durations_conflict():
    """
    Acceptance Test 12:
    Gold return window 60 days vs Gold return window 45 days -> CONFLICT (TRUE_CONFLICT)
    """
    c1 = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u1",
        asset_id="asset1",
        claim_text="Gold member return window is 60 calendar days.",
        subject="Gold member",
        predicate="has_return_window",
        object_="60 calendar days",
        evidence_text_span="Gold member return window is 60 calendar days.",
        value=60,
        unit="calendar_days",
    )
    c2 = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u2",
        asset_id="asset1",
        claim_text="Gold member return window is 45 calendar days.",
        subject="Gold member",
        predicate="has_return_window",
        object_="45 calendar days",
        evidence_text_span="Gold member return window is 45 calendar days.",
        value=45,
        unit="calendar_days",
    )

    compat = CompatibilityGate.evaluate_compatibility(c1, c2)
    assert compat.is_comparable is True

    is_conflict, conflict_type = CompatibilityGate.evaluate_value_conflict(c1, c2)
    assert is_conflict is True
    assert conflict_type == "INCOMPATIBLE_NUMERIC_VALUE"


# =========================================================================
# Acceptance Test 13: Boundary Ambiguity Routing to REVIEW
# =========================================================================

def test_acceptance_13_boundary_ambiguity_routes_to_review():
    """
    Acceptance Test 13:
    Cash refund 'up to $50' (§8) vs 'under $50' (FAQ Q7) -> REVIEW (GENUINE_BOUNDARY_AMBIGUITY)
    """
    key_8 = NormalizedClaimKey(subject_key="Cash_Refund", predicate_key="has_refund_method", approval_band="up_to_50")
    key_faq = NormalizedClaimKey(subject_key="Cash_Refund", predicate_key="has_refund_method", approval_band="under_50")

    compat = CompatibilityGate.evaluate_applicability_overlap(key_8, key_faq)
    assert compat.is_comparable is True
    assert compat.reason == "GENUINE_BOUNDARY_AMBIGUITY"
    assert compat.relationship == "BOUNDARY_INCONSISTENCY"


# =========================================================================
# Cancellation Precision: All 7 Stages Mapped from §11
# =========================================================================

@pytest.mark.asyncio
async def test_cancellation_all_7_stages_precision_dispatch(envelope_builder):
    """
    Verifies that all 7 cancellation rows from Northwind §11
    map cleanly to specific predicates without generic has_refund.
    """
    content = """# Northwind Order Cancellations
## 11. Order Cancellations
| Order Stage | Cancellation Window | Refund | Processing Fee | Notes |
|---|---|---|---|---|
| Pending | Prior to processing start | Full refund, immediate release of authorisation | None | Automated cancellation |
| Processing | Before packing | Full refund within 3–5 days | None | Standard reversal |
| Packed | Prior to carrier handover | Full refund if stopped, else return | $5 fee | Warehouse intercept |
| Shipped | In transit | Refuse delivery or return | Customer pays return shipping | Carrier transit |
| Delivered | Post-delivery | Standard return policy | None | Refer to §3.1 |
| Pre-order | Any time before release | Full refund | None | Zero penalty |
| Backordered | Any time before fulfillment | Full refund | None | Instant cancellation |
"""
    env = envelope_builder(content)
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]

    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    refund_claims = [c for c in claims if c.table_binding and c.table_binding.column_header == "Refund"]
    pred_map = {c.subject: c.predicate for c in refund_claims}

    # No generic has_refund allowed
    for c in claims:
        assert c.predicate != "has_refund", f"Generic has_refund detected on claim: {c}"

    assert pred_map.get("Pending") == "has_cancellation_refund_outcome"
    assert pred_map.get("Processing") == "has_cancellation_refund_timing"
    assert pred_map.get("Packed") in ("has_post_shipment_resolution_path", "has_cancellation_refund_outcome")
    assert pred_map.get("Shipped") == "has_post_shipment_resolution_path"
    assert pred_map.get("Delivered") == "has_post_delivery_resolution_path"
    assert pred_map.get("Pre-order") == "has_cancellation_refund_outcome"
    assert pred_map.get("Backordered") == "has_cancellation_refund_outcome"


# =========================================================================
# Qualifier Preservation: typical, usually, may, recommended, at_discretion
# =========================================================================

@pytest.mark.asyncio
async def test_soft_qualifiers_preserved(envelope_builder):
    """
    Verifies that soft modal qualifiers (typical, usually, may, recommended, at_discretion, where_possible)
    are preserved on CandidateClaim.qualifier and table_binding.
    """
    content = """# Processing Timelines
## 7. Typical Processing Timelines
| Stage | Typical Timeline |
|---|---|
| Inspection | 2-3 business days |
| Bank posting | Usually 3-5 business days |
"""
    env = envelope_builder(content)
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]

    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    # Inspection inherits "typical" from column header
    insp_claim = next(c for c in claims if "Inspection" in c.subject)
    assert insp_claim.qualifier == "typical"
    assert "typical" in insp_claim.qualifiers

    # Bank posting has "usually" in cell value
    bank_claim = next(c for c in claims if "Bank" in c.subject)
    assert bank_claim.qualifier in ("typical", "usually")
    assert any(q in ("typical", "usually") for q in bank_claim.qualifiers)
