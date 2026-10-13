"""
NIST AI RMF Ground-Truth Benchmark Suite for Enterprise Document Intelligence.

Evaluates:
1. Zero-Token Extraction Ratio (target: 100% on tabular policies).
2. Table Grid Coordinate Fidelity (target: 100% on cell, row, and column binding).
3. Soft Qualifier Retention ('up to', 'typical', 'discretionary').
4. Non-Canonical Isolation Rate (revision history, FAQs, contact info safely isolated).
5. Conflict Engine False-Positive Rate (0.0% on mutually exclusive conditions).
"""

import sys
import uuid
from typing import List
import pytest

from app.ingestion.universal_file_parser import UniversalFileParser
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.models import CandidateClaim, TableGridBinding
from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.conflict_engine.normalizer import NormalizedClaimKey
from app.validation_gate.evaluators import CompletenessEvaluator
from app.validation_gate.models import DecisionCode


@pytest.fixture
def sample_notice_policy_markdown() -> str:
    return """# Employee Notice Period Policy

## Statement of Confidentiality
This document contains confidential and proprietary information.

## Table of Contents
| Section | Title | Scope |
|---|---|---|
| Section 1 | Purpose | Objectives |
| Section 3 | Policy Framework | Operational requirements |

## 1. Purpose
Our notice period policy is designed to ensure smooth transitions across all organizational departures.

## 2. Applicability
The policy applies to all Permanent Employees, Interns & Contractors.

## 3. Policy Framework
Wingify has defined notice period durations for employees based on the Levels & Grades Framework:

| Level & Grade | Group Category | Maximum Duration Confirmed | Probationers |
|---|---|---|---|
| A (A1 & A2) | CXO | 90 Days | |
| B (B1 & B2) | Senior Management | 90 Days | |
| C (C1, C2 & C3) | Middle Management | 60 Days | 15 days |
| D (D1, D2 & D3) | Junior Management | 30 Days | |
| E (E1, E2 & E3) | Fellow | 30 Days | |

## 4. Reference
This policy operates in conjunction with related enterprise governance documents.

## Document Revision History
| Ver # | Ver. Date | Description | Prepared By | Approved By |
|---|---|---|---|---|
| 1.0 | 19-Jun-2017 | First Release | People Success | CEO |
| 1.5 | 15-Jan-2025 | Comprehensive Policy Revision | People Success | CEO |
"""


@pytest.fixture
def sample_northwind_policy_markdown() -> str:
    return """# Northwind Outfitters Inc. Refund & Return Policy

## 2. Definitions
| Term | Definition |
|---|---|
| Refund | Return of money to the original payment method or store credit |
| Return | Sending a purchased item back to Northwind by mail or in-store drop-off |
| Exchange | Replacing an item with a different size, colour or product |

## 3. Standard Return Policy
### 3.1 Extended windows
| Category / Situation | Return Window |
|---|---|
| Standard merchandise | 30 days |
| Northwind Rewards Gold members | 60 days |
| Footwear (worn indoors only) | 45 days |
| Camping tents and sleeping bags (unused) | 60 days |

## 8. Refund Methods and Payment Types
| Original payment | Refund method | Notes |
|---|---|---|
| Visa / Mastercard / Amex | Original card | 3-5 business days to post |
| Debit card | Original card | Up to 10 business days |
| PayPal | PayPal balance | Usually within 24 hours |
| Cash (in-store) | Cash up to $50, then store credit/card | ID required over $50 |

## 14. Warranty Claims vs. Refunds
| Product Category | Warranty period | Remedy |
|---|---|---|
| Tents and shelters | 2 years | Repair, replace or refund |
| Backpacks | 5 years | Repair or replace |
| Footwear | 1 year | Replace or refund |

## 19. Contact Information and Escalation
| Channel | Details | Hours (Pacific Time) |
|---|---|---|
| Phone (US/Canada) | 1-800-555-0142 | Mon-Fri 8am-8pm |
| Email | support@northwind-demo.example | Response within 24 hours |
"""


@pytest.mark.asyncio
async def test_notice_period_matrix_golden_benchmark(sample_notice_policy_markdown):
    """
    Benchmark 1: Notice Period Matrix Golden Label Fidelity.
    Verifies:
    - 100% extraction of the 6 governing notice rules.
    - Exact 2D TableGridBinding coordinates on each claim.
    - Zero tokens consumed.
    - Zero false-positive conflicts between Grade C confirmed (60d) vs probationary (15d).
    """
    env = EnvelopeFactory.create_from_file_upload(
        filename="notice_policy.md",
        raw_bytes=sample_notice_policy_markdown.encode("utf-8"),
        parsed_content=sample_notice_policy_markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )

    parsed = await DocumentParser.parse(env)
    assert len(parsed.units) > 0

    claims: List[CandidateClaim] = []
    for u in parsed.units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    # 1. Zero-Token Ratio: 100% of claims extracted via deterministic schema/table strategies
    zero_token_claims = [c for c in claims if c.extraction_strategy.value in ("deterministic_schema", "table_aware")]
    assert len(zero_token_claims) == len(claims)

    # 2. Extract governing policy rules
    policy_rules = [c for c in claims if c.content_role == ContentRole.POLICY_RULE and c.is_canonical]
    assert len(policy_rules) == 6, f"Expected 6 notice policy claims, got {len(policy_rules)}"

    # 3. Verify TableGridBinding fidelity
    for c in policy_rules:
        assert c.table_binding is not None
        assert isinstance(c.table_binding, TableGridBinding)
        assert c.table_binding.table_id != ""
        assert c.table_binding.row_key != ""
        assert c.table_binding.column_header != ""
        assert c.table_binding.normalized_value in (90, 60, 30, 15)
        assert c.table_binding.normalized_unit == "days"

    # 4. Verify Grade C Ground Truth
    grade_c_claims = [c for c in policy_rules if "Grade C" in c.subject]
    assert len(grade_c_claims) == 2, "Grade C should have exactly 2 claims (confirmed & probationary)"

    confirmed_c = next(c for c in grade_c_claims if c.predicate == "has_confirmed_notice_duration")
    probation_c = next(c for c in grade_c_claims if c.predicate == "has_probationary_notice_duration")

    assert confirmed_c.value == 60
    assert probation_c.value == 15
    assert "Confirmed status" in confirmed_c.conditions
    assert "Probationary status" in probation_c.conditions

    # 5. Verify Pre-LLM Compatibility Gate on Grade C
    # Comparing confirmed_c against probation_c must yield is_comparable=False
    # because their predicates and conditions are mutually exclusive!
    outcome = CompatibilityGate.evaluate_compatibility(confirmed_c, probation_c)
    assert outcome.is_comparable is False, f"Expected is_comparable=False, got {outcome}"
    assert outcome.reason in ("NON_OVERLAPPING_CONDITIONAL_SCOPE", "ORTHOGONAL_PREDICATES", "DISJOINT_APPLICABILITY_SCOPE")
    assert outcome.relationship in ("COMPLEMENTARY_CONDITIONAL_RULES", "INDEPENDENT_PREDICATES")


@pytest.mark.asyncio
async def test_northwind_multi_matrix_and_qualifier_benchmark(sample_northwind_policy_markdown):
    """
    Benchmark 2: Multi-Domain Matrix Extraction & Soft Qualifier Retention.
    Verifies:
    - Return windows extracted with scalar and unit.
    - Soft qualifiers ('up to', 'typical') retained in TableGridBinding and CandidateClaim.
    - Definitions and Contact Info classified into non-canonical roles.
    """
    env = EnvelopeFactory.create_from_file_upload(
        filename="northwind_policy.md",
        raw_bytes=sample_northwind_policy_markdown.encode("utf-8"),
        parsed_content=sample_northwind_policy_markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
    )

    parsed = await DocumentParser.parse(env)
    claims: List[CandidateClaim] = []
    for u in parsed.units:
        claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    # 1. Return Window Claims
    return_window_claims = [c for c in claims if c.predicate == "has_return_window"]
    assert len(return_window_claims) == 4

    std_claim = next(c for c in return_window_claims if "Standard merchandise" in c.subject)
    assert std_claim.value == 30
    assert std_claim.unit == "days"

    gold_claim = next(c for c in return_window_claims if "Gold members" in c.subject)
    assert gold_claim.value == 60
    assert gold_claim.unit == "days"

    # 2. Soft Qualifiers Retention
    # Debit card has 'Up to 10 business days'
    debit_claim = next((c for c in claims if "Debit card" in c.subject and ("notes" in c.predicate or "timeline" in c.predicate)), None)
    assert debit_claim is not None, "Debit card notes/timeline claim not found"
    assert "up_to" in debit_claim.qualifiers
    assert debit_claim.table_binding.qualifiers == ["up_to"]

    # PayPal has 'Usually within 24 hours'
    paypal_claim = next((c for c in claims if "PayPal" in c.subject and ("notes" in c.predicate or "timeline" in c.predicate)), None)
    assert paypal_claim is not None, "PayPal notes/timeline claim not found"
    assert "typical" in paypal_claim.qualifiers or "within" in paypal_claim.qualifiers

    # 3. Non-Canonical Isolation
    # Definitions must be non-canonical
    def_claims = [c for c in claims if c.content_role == ContentRole.DEFINITION]
    assert len(def_claims) >= 3
    for dc in def_claims:
        assert dc.is_canonical is False

    # Contact channels must be non-canonical
    contact_claims = [c for c in claims if c.content_role == ContentRole.CONTACT_INFO]
    assert len(contact_claims) >= 2
    for cc in contact_claims:
        assert cc.is_canonical is False


def test_anti_fragment_completeness_benchmark():
    """
    Benchmark 3: Anti-Fragment Gate Evaluation.
    Verifies that ungrounded fragments (missing subjects, pronoun references, missing predicates)
    are strictly rejected with DecisionCode.FRAGMENT_ASSERTION_DISCARDED.
    """
    # Fragment with ungrounded pronoun subject "It"
    pronoun_claim = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u_frag_1",
        asset_id="asset_1",
        claim_text="It must be completed within 30 days.",
        subject="It",
        predicate="must_be_completed",
        object_="30 days",
        evidence_text_span="It must be completed within 30 days.",
    )
    res_pronoun = CompletenessEvaluator.evaluate(pronoun_claim)
    assert res_pronoun.passed is False
    assert res_pronoun.details.get("is_fragment") is True
    assert "ungrounded pronoun" in res_pronoun.reason

    # Fragment with bare incomplete predicate "is"
    incomplete_pred_claim = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u_frag_2",
        asset_id="asset_1",
        claim_text="Standard merchandise is 30 days.",
        subject="Standard merchandise",
        predicate="is",
        object_="30 days",
        evidence_text_span="Standard merchandise is 30 days.",
    )
    res_pred = CompletenessEvaluator.evaluate(incomplete_pred_claim)
    assert res_pred.passed is False
    assert res_pred.details.get("is_fragment") is True
    assert "lacks normative relation" in res_pred.reason

    # Grounded complete claim
    complete_claim = CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id="u_good_1",
        asset_id="asset_1",
        claim_text="Standard merchandise has a return window of 30 days.",
        subject="Standard merchandise",
        predicate="has_return_window",
        object_="30 days",
        evidence_text_span="Standard merchandise | Return Window: 30 days",
        value=30,
        unit="days",
    )
    res_good = CompletenessEvaluator.evaluate(complete_claim)
    assert res_good.passed is True
    assert res_good.status == "complete"
