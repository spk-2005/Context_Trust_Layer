"""
Enterprise Claim Contract Benchmark Suite.

Verifies:
1. Strict row-entity binding (no false 'subscription' on 'Missing original box').
2. Canonical predicate registry (ID verification, allocation rules, provider timelines, cross-references).
3. Cancellation stages (outcomes, timings, post-shipment/delivery resolution paths).
4. Strongly typed values (TypedValue for durations, ranges, calendar deadlines).
5. 5-Gate applicability conflict filter (eliminates all 9 false-conflict pairs).
6. True conflict detection (Gold members 60d vs 45d).
7. Boundary ambiguity routing (cash refund up to $50 vs under $50).
"""

import uuid
import pytest
from app.extraction.models import CandidateClaim, TableGridBinding, TypedValue
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.conflict_engine.normalizer import ClaimNormalizer


@pytest.mark.asyncio
async def test_fixture_1_missing_box_no_subscription_contamination():
    """Fixture 1: Returned item condition must NOT inherit subscription subject."""
    markdown = """# Northwind Refund Percentages
## 4. Refund Percentages
| Item Condition | Refund Percentage |
|---|---|
| Missing original box (non-fragile) | 60% |
"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="refund_pct.md",
        raw_bytes=markdown.encode("utf-8"),
        parsed_content=markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    assert len(table_units) == 1

    claims = DeterministicSchemaExtractor.extract_from_unit(table_units[0])
    assert len(claims) == 1
    claim = claims[0]
    assert "subscription" not in claim.subject.lower(), f"Subject was contaminated: {claim.subject}"
    assert "Missing original box" in claim.subject
    assert claim.predicate == "has_refund_percentage"
    assert claim.value == 60 or claim.value == "60"


@pytest.mark.asyncio
async def test_fixture_2_cash_id_verification_requirement():
    """Fixture 2: Cash notes requiring ID routes to has_identity_verification_requirement."""
    markdown = """# Payment Methods
## 8. Payment Methods
| Original Payment | Refund Method | Notes |
|---|---|---|
| Cash (in-store) | Cash up to $50, then store credit | ID required over $50 |
"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="pm.md",
        raw_bytes=markdown.encode("utf-8"),
        parsed_content=markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    assert len(table_units) == 1

    claims = DeterministicSchemaExtractor.extract_from_unit(table_units[0])
    id_claim = next((c for c in claims if c.predicate == "has_identity_verification_requirement"), None)
    assert id_claim is not None, f"Expected has_identity_verification_requirement, got {[c.predicate for c in claims]}"
    assert "ID required over $50" in id_claim.object


@pytest.mark.asyncio
async def test_fixture_3_split_payment_allocation_rule():
    """Fixture 3: Split payment allocation order routes to has_refund_allocation_rule."""
    markdown = """# Payment Methods
## 8. Payment Methods
| Original Payment | Refund Method | Notes |
|---|---|---|
| Split payment | Original methods | Gift card portion first, remainder to credit card |
"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="split_pm.md",
        raw_bytes=markdown.encode("utf-8"),
        parsed_content=markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    claims = DeterministicSchemaExtractor.extract_from_unit(table_units[0])
    alloc_claim = next((c for c in claims if c.predicate == "has_refund_allocation_rule"), None)
    assert alloc_claim is not None, f"Expected has_refund_allocation_rule, got {[c.predicate for c in claims]}"
    assert "Gift card portion first" in alloc_claim.object


@pytest.mark.asyncio
async def test_fixture_4_bnpl_provider_governed_timeline():
    """Fixture 4: BNPL third-party timeline routes to has_provider_governed_timeline."""
    markdown = """# Payment Methods
## 8. Payment Methods
| Original Payment | Typical Posting Time | Notes |
|---|---|---|
| Buy Now Pay Later (BNPL) | Provider timelines apply | Provider timelines apply |
"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="bnpl.md",
        raw_bytes=markdown.encode("utf-8"),
        parsed_content=markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    claims = DeterministicSchemaExtractor.extract_from_unit(table_units[0])
    bnpl_claim = next((c for c in claims if c.predicate == "has_provider_governed_timeline"), None)
    assert bnpl_claim is not None, f"Expected has_provider_governed_timeline, got {[c.predicate for c in claims]}"


@pytest.mark.asyncio
async def test_fixture_5_regional_policy_internal_cross_reference():
    """Fixture 5: Regional policy pointer routes to has_internal_policy_reference."""
    markdown = """# Regional Policies
## 15. Regional Policies
| Country / Region | Return Window | Notes / Reference |
|---|---|---|
| United States | 30 days | See Section 9 |
"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="regional.md",
        raw_bytes=markdown.encode("utf-8"),
        parsed_content=markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    claims = DeterministicSchemaExtractor.extract_from_unit(table_units[0])
    ref_claim = next((c for c in claims if c.predicate == "has_internal_policy_reference"), None)
    assert ref_claim is not None, f"Expected has_internal_policy_reference, got {[c.predicate for c in claims]}"
    assert "Section 9" in ref_claim.cross_references
    assert ref_claim.typed_value is not None
    assert ref_claim.typed_value.value_type == "REFERENCE"
    assert ref_claim.typed_value.reference_id == "section_9"


@pytest.mark.asyncio
async def test_fixture_6_cancellation_stages_and_resolution_paths():
    """Fixture 6: Order cancellation stages dispatch to outcome, timing, and resolution paths."""
    markdown = """# Order Cancellations
## 11. Order Cancellations
| Order Stage | Cancellation Outcome |
|---|---|
| Pending processing | Full refund |
| Shipped in transit | Customer must refuse delivery |
| Delivered | Standard return policy |
"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="canc.md",
        raw_bytes=markdown.encode("utf-8"),
        parsed_content=markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    pending_c = next(c for c in claims if "Pending" in c.subject)
    assert pending_c.predicate == "has_cancellation_refund_outcome"

    shipped_c = next(c for c in claims if "Shipped" in c.subject)
    assert shipped_c.predicate == "has_post_shipment_resolution_path"

    delivered_c = next(c for c in claims if "Delivered" in c.subject)
    assert delivered_c.predicate == "has_post_delivery_resolution_path"


@pytest.mark.asyncio
async def test_fixture_7_typed_value_serialization():
    """Fixture 7: Strongly typed values for percentages, ranges, and calendar dates."""
    markdown = """# Policy Constraints
## 4. Refund Percentages
| Item Condition | Refund Percentage |
|---|---|
| Light wear | 50% - 75% |
| Damaged by customer | Not eligible |
"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="pct.md",
        raw_bytes=markdown.encode("utf-8"),
        parsed_content=markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )
    parsed = await DocumentParser.parse(env)
    table_units = [u for u in parsed.units if u.block_type == "table_row"]
    claims = []
    for u in table_units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    light_claim = next(c for c in claims if "Light wear" in c.subject)
    assert light_claim.typed_value is not None
    assert light_claim.typed_value.value_type == "PERCENTAGE"
    assert light_claim.typed_value.scalar_min == 50.0
    assert light_claim.typed_value.scalar_max == 75.0
    assert light_claim.typed_value.unit == "%"


def test_fixture_8_applicability_gate_eliminates_all_false_conflict_pairs():
    """Fixture 8: 5-Gate applicability check eliminates all 9 false-conflict pairs."""
    env_id = uuid.uuid4()

    def make_claim(subject, predicate, obj, text, value=None, unit=None):
        return CandidateClaim.create(
            envelope_id=env_id,
            unit_id=str(uuid.uuid4()),
            asset_id="doc.md",
            claim_text=text,
            subject=subject,
            predicate=predicate,
            object_=obj,
            evidence_text_span=text,
            value=value,
            unit=unit,
        )

    # 1. Process stage: return transit (3-7 days) vs warehouse inspection (1-2 days)
    c1a = make_claim("Return transit", "has_stage_duration", "3-7 days", "Return transit duration is 3-7 days.", 5, "days")
    c1b = make_claim("Warehouse inspection", "has_stage_duration", "1-2 days", "Warehouse inspection duration is 1-2 days.", 2, "days")
    out1 = CompatibilityGate.evaluate_compatibility(c1a, c1b)
    assert out1.is_comparable is False
    assert out1.reason == "DIFFERENT_PROCESS_STAGE"

    # 2. Payment method: Credit card (3-5 days) vs Debit card (5-10 days)
    c2a = make_claim("Credit card", "has_posting_duration", "3-5 days", "Credit card posting duration is 3-5 days.", 5, "days")
    c2b = make_claim("Debit card", "has_posting_duration", "5-10 days", "Debit card posting duration is 5-10 days.", 10, "days")
    out2 = CompatibilityGate.evaluate_compatibility(c2a, c2b)
    assert out2.is_comparable is False
    assert out2.reason == "DIFFERENT_PAYMENT_METHOD"

    # 3. Policy domain: Missing box (60%) vs Trailhead Box (48 hrs)
    c3a = make_claim("Missing original box (non-fragile)", "has_refund_percentage", "60%", "Missing original box specifies 60% refund.", 60, "%")
    c3b = make_claim("Trailhead Box subscription", "has_cancellation_rule", "48 hours", "Trailhead Box subscription specifies cancellation within 48 hours.", 48, "hours")
    out3 = CompatibilityGate.evaluate_compatibility(c3a, c3b)
    assert out3.is_comparable is False
    assert out3.reason == "DIFFERENT_POLICY_DOMAIN"

    # 4. Item condition: Light wear (50-75%) vs Heavy use (0-25%)
    c4a = make_claim("Light wear", "has_refund_percentage", "50-75%", "Light wear refund percentage is 50-75%.", 60, "%")
    c4b = make_claim("Heavy use", "has_refund_percentage", "0-25%", "Heavy use refund percentage is 0-25%.", 15, "%")
    out4 = CompatibilityGate.evaluate_compatibility(c4a, c4b)
    assert out4.is_comparable is False
    assert out4.reason == "DIFFERENT_ITEM_CONDITION"

    # 5. Approval band: Over $500 vs $100.01 - $500
    c5a = make_claim("Executive Approval", "has_approval_requirement", "over $500", "Refunds over $500 require executive approval.")
    c5b = make_claim("Manager Approval", "has_approval_requirement", "$100 to $500", "Refunds between $100 to $500 require manager approval.")
    out5 = CompatibilityGate.evaluate_compatibility(c5a, c5b)
    assert out5.is_comparable is False
    assert out5.reason == "DISJOINT_APPROVAL_BANDS"

    # 6. Risk band: Return rate 30-40% vs Return rate > 40%
    c6a = make_claim("Customer Tier Review", "has_risk_action", "warning", "Customers with return rate 30-40% receive warning.")
    c6b = make_claim("Account Suspension", "has_risk_action", "suspend", "Customers with return rate over 40% face account suspension.")
    out6 = CompatibilityGate.evaluate_compatibility(c6a, c6b)
    assert out6.is_comparable is False
    assert out6.reason == "DISJOINT_RISK_BANDS"

    # 7. Contact channel: US/Canada phone vs UK phone
    c7a = make_claim("Phone Support", "has_phone_number", "1-800-555-0142", "Phone (US/Canada) support is 1-800-555-0142.")
    c7b = make_claim("Phone Support", "has_phone_number", "0800-123-456", "Phone (UK) support is 0800-123-456.")
    out7 = CompatibilityGate.evaluate_compatibility(c7a, c7b)
    assert out7.is_comparable is False
    assert out7.reason == "DIFFERENT_SERVICE_CHANNEL"

    # 8. Service channel: Email (24h) vs Chat (< 2m)
    c8a = make_claim("Customer Service", "has_response_time", "24 hours", "Email customer service responds within 24 hours.", 24, "hours")
    c8b = make_claim("Customer Service", "has_response_time", "2 minutes", "Chat customer service responds within 2 minutes.", 2, "minutes")
    out8 = CompatibilityGate.evaluate_compatibility(c8a, c8b)
    assert out8.is_comparable is False
    assert out8.reason == "DIFFERENT_SERVICE_CHANNEL"

    # 9. Chargeback stage: Evidence submission (7d) vs Issuer decision (30-90d)
    c9a = make_claim("Evidence submission", "has_stage_duration", "7 days", "Evidence submission timeline is 7 days.", 7, "days")
    c9b = make_claim("Issuer decision", "has_stage_duration", "30-90 days", "Issuer decision timeline is 30-90 days.", 60, "days")
    out9 = CompatibilityGate.evaluate_compatibility(c9a, c9b)
    assert out9.is_comparable is False
    assert out9.reason == "DIFFERENT_PROCESS_STAGE"


def test_fixture_9_true_conflict_detection_on_competing_claims():
    """Fixture 9: True conflict on Gold members return window (60d vs 45d)."""
    env_id = uuid.uuid4()
    c_gold_60 = CandidateClaim.create(
        envelope_id=env_id,
        unit_id="u_gold_1",
        asset_id="northwind_handbook.pdf",
        claim_text="Northwind Rewards Gold members have a return window of 60 days.",
        subject="Northwind Rewards Gold members",
        predicate="has_return_window",
        object_="60 days",
        evidence_text_span="Gold members | 60 days",
        value=60,
        unit="days",
    )
    c_gold_45 = CandidateClaim.create(
        envelope_id=env_id,
        unit_id="u_gold_2",
        asset_id="northwind_faq.pdf",
        claim_text="Northwind Rewards Gold members have a return window of 45 days.",
        subject="Northwind Rewards Gold members",
        predicate="has_return_window",
        object_="45 days",
        evidence_text_span="Gold members | 45 days",
        value=45,
        unit="days",
    )

    compat = CompatibilityGate.evaluate_compatibility(c_gold_60, c_gold_45)
    assert compat.is_comparable is True
    assert compat.reason == "COMPETING_DECISION_KEYS"

    is_conflict, conflict_type = CompatibilityGate.evaluate_value_conflict(c_gold_60, c_gold_45)
    assert is_conflict is True
    assert conflict_type == "INCOMPATIBLE_NUMERIC_VALUE"


def test_fixture_10_boundary_ambiguity_routing_to_review():
    """Fixture 10: Cash refund 'up to $50' vs 'under $50' routed to REVIEW."""
    env_id = uuid.uuid4()
    c_policy = CandidateClaim.create(
        envelope_id=env_id,
        unit_id="u_cash_1",
        asset_id="refund_policy.pdf",
        claim_text="Cash refund is permitted in-store up to $50.",
        subject="Cash refunds",
        predicate="has_refund_method",
        object_="up to $50",
        evidence_text_span="Cash refund is permitted in-store up to $50.",
        value=50,
        unit="USD",
    )
    c_faq = CandidateClaim.create(
        envelope_id=env_id,
        unit_id="u_cash_2",
        asset_id="customer_faq.pdf",
        claim_text="Cash refunds are only available in-store for amounts under $50.",
        subject="Cash refunds",
        predicate="has_refund_method",
        object_="under $50",
        evidence_text_span="Cash refunds are only available in-store for amounts under $50.",
        value=50,
        unit="USD",
    )

    compat = CompatibilityGate.evaluate_compatibility(c_policy, c_faq)
    assert compat.is_comparable is True
    assert compat.reason == "GENUINE_BOUNDARY_AMBIGUITY"

    is_conflict, conflict_type = CompatibilityGate.evaluate_value_conflict(c_policy, c_faq)
    assert is_conflict is True
    assert conflict_type == "GENUINE_BOUNDARY_AMBIGUITY"
