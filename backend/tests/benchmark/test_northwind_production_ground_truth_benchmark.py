"""
Production Ground-Truth Benchmark for Northwind Policy Extraction & Validation.

Directly tests the resolution of all defects identified in Perplexity's audit:
1. Defect #88: RMA definition fragment prevention via safe abbreviation shielding.
2. Defects #85, #86: Non-canonical isolation of FAQ questions via QUESTION_NOT_ASSERTION knockout gate.
3. Defect #87: Complete elimination of cross-tenant 'Wingify Shipping Costs' contamination in Northwind.
4. Defects #24, #32, #33: HEADING_NON_CANONICAL and INTRODUCTORY_CONTEXT isolation.
5. Defect #10: Atomic decomposition of compound eligibility meta-rules into 3 executable obligations.
6. Defects #20–#22: Structured cumulative approval thresholds (§4.2) and fraud review isolation.
7. Defects #2, #3, #23: Weak grammatical predicates (override, start, verify, be) mapped to canonical registry.
8. Boundary Ambiguity: 'up to $50' vs 'under $50' routes to REVIEW with GENUINE_BOUNDARY_AMBIGUITY.
"""

from __future__ import annotations

import uuid
import pytest

from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.conflict_engine.normalizer import NormalizedClaimKey
from app.db.enums import SourceFamily, SourceIntent
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit
from app.extraction.subject_normalizer import SubjectNormalizer
from app.validation_gate.decision_engine import ClaimLifecycleDecision, ClaimLifecycleDecisionEngine
from app.validation_gate.evaluators import CompletenessEvaluator
from app.validation_gate.models import DecisionCode


@pytest.fixture
def northwind_envelope_factory():
    def _create(content: str, filename: str = "Northwind_Handbook.md") -> CanonicalSourceEnvelope:
        return EnvelopeFactory.create_from_file_upload(
            filename=filename,
            raw_bytes=content.encode("utf-8"),
            parsed_content=content,
            organization_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            document_type="policy",
            source_intent=SourceIntent.GOVERNANCE_POLICY,
        )
    return _create


# =========================================================================
# 1. Defect #88: RMA Definition Fragment & Abbreviation Shielding
# =========================================================================

@pytest.mark.asyncio
async def test_defect_88_rma_definition_fragment_elimination(northwind_envelope_factory):
    """
    Defect #88: Sentence boundary splitter must NOT split on period in 'e.g.',
    which previously created the split fragment 'RMA Return Merchandise Authorization number, e.g.'.
    Verifies that the entire definition statement is preserved intact with example RMA-2026-004815.
    """
    content = """# Northwind Returns Procedure

RMA: Return Merchandise Authorization number, e.g. RMA-2026-004815, required for all mailed returns.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]
    assert len(units) >= 1

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    assert len(extracted_claims) >= 1
    rma_claim = next((c for c in extracted_claims if "rma" in c.subject.lower()), None)
    assert rma_claim is not None, "RMA definition claim must be extracted"

    # Verifies sentence was NOT cut off at e.g.
    assert not rma_claim.claim_text.strip().endswith("e.g.")
    assert not rma_claim.claim_text.strip().endswith("e.g.,")
    assert rma_claim.predicate == "has_definition"
    assert rma_claim.claim_type == "definition"
    assert rma_claim.content_role == ContentRole.DEFINITION
    assert rma_claim.is_canonical is False

    # Example value RMA-2026-004815 extracted into structured data
    assert rma_claim.structured_values.get("example_value") == "RMA-2026-004815"

    # CompletenessEvaluator passes intact claim
    eval_res = CompletenessEvaluator.evaluate(rma_claim)
    assert eval_res.passed is True

    # Synthetic orphan fragment must be KNOCKED OUT
    orphan_frag = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_frag",
        asset_id=env.asset_id,
        claim_text="RMA Return Merchandise Authorization number, e.g.",
        subject="RMA",
        predicate="has_definition",
        object_="Return Merchandise Authorization number, e.g.",
        evidence_text_span="RMA Return Merchandise Authorization number, e.g.",
    )
    eval_frag = CompletenessEvaluator.evaluate(orphan_frag)
    assert eval_frag.passed is False
    assert eval_frag.details.get("decision_code") == DecisionCode.DEFINITION_FRAGMENT.value


# =========================================================================
# 2. Defects #85, #86: FAQ Questions Non-Canonical Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_defects_85_86_faq_questions_isolated_from_canonical_claims(northwind_envelope_factory):
    """
    Defects #85, #86: FAQ inquiries ('Will I get my shipping cost back?') must NOT
    be promoted as canonical normative policy obligations.
    Verifies QUESTION_NOT_ASSERTION knockout gate and candidate discovery isolation.
    """
    content = """# Northwind Policies

## 15. Frequently Asked Questions
Will I get my shipping cost back?
Original outbound shipping charges are non-refundable unless the return is due to an error on our part.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)

    # 1. Candidate discovery must reject interrogative units
    q_unit = next((u for u in parsed.units if "?" in (u.content_text or "")), None)
    assert q_unit is not None
    is_cand, strat, reason = CandidateDiscoveryEngine.is_candidate(q_unit)
    assert is_cand is False
    assert "inquiry" in reason.lower() or "non-canonical" in reason.lower()

    # 2. Even if candidate claim is formed, CompletenessEvaluator must knock it out
    cand_q = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id=q_unit.unit_id,
        asset_id=env.asset_id,
        claim_text="Will I get my shipping cost back?",
        subject="Customer Shipping",
        predicate="covers_shipping_costs",
        object_="shipping cost back",
        evidence_text_span="Will I get my shipping cost back?",
        content_role=ContentRole.FAQ_QUESTION,
    )
    eval_res = CompletenessEvaluator.evaluate(cand_q)
    assert eval_res.passed is False
    assert eval_res.details.get("decision_code") == DecisionCode.QUESTION_NOT_ASSERTION.value

    # 3. DecisionEngine routes to hard REJECT
    decision = ClaimLifecycleDecisionEngine.evaluate_candidate(
        candidate=cand_q,
        envelope=env,
    )
    assert decision.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert decision.decision_code == DecisionCode.QUESTION_NOT_ASSERTION


# =========================================================================
# 3. Defect #87: Eradication of Cross-Tenant 'Wingify Shipping Costs'
# =========================================================================

@pytest.mark.asyncio
async def test_defect_87_cross_tenant_subject_contamination_eliminated(northwind_envelope_factory):
    """
    Defect #87: Northwind return shipping clauses previously extracted subject='Wingify Shipping Costs'.
    Verifies that Northwind clauses produce tenant-appropriate subjects ('Customer Return Shipping'),
    and the SUBJECT_CONTAMINATION knockout gate rejects any ungrounded tenant injection.
    """
    content = """# Northwind Shipping Guidelines

Customer is responsible for return shipping costs unless the return is due to damaged or defective items.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]
    assert len(units) >= 1

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    assert len(extracted_claims) >= 1
    shipping_claim = next((c for c in extracted_claims if "shipping" in c.claim_text.lower()), None)
    assert shipping_claim is not None

    # Wingify must NEVER appear in Northwind extracted subject
    assert "wingify" not in shipping_claim.subject.lower()
    assert shipping_claim.subject == "Customer Return Shipping"
    assert shipping_claim.predicate == "responsible_for_shipping_costs"
    assert shipping_claim.modality == "OBLIGATION"

    # SUBJECT_CONTAMINATION gate verifies cross-tenant injection is rejected
    contaminated_claim = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_contam",
        asset_id=env.asset_id,
        claim_text="Customer is responsible for return shipping costs.",
        subject="Wingify Shipping Costs",
        predicate="responsible_for_shipping_costs",
        object_="return shipping costs",
        evidence_text_span="Customer is responsible for return shipping costs.",
    )
    eval_contam = CompletenessEvaluator.evaluate(contaminated_claim)
    assert eval_contam.passed is False
    assert eval_contam.details.get("decision_code") == DecisionCode.SUBJECT_CONTAMINATION.value


# =========================================================================
# 4. Defects #24, #32, #33: Headings & Introductory Context Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_defects_24_32_33_headings_and_introductory_context_isolation(northwind_envelope_factory):
    """
    Defects #24, #32, #33: Section titles ('How to Request a Refund', 'Refund Methods and Payment Types')
    must NOT be promoted into canonical policy claims.
    Verifies HEADING_NON_CANONICAL knockout gate.
    """
    content = """# Northwind Handbook

## How to Request a Refund
The primary purpose of this section is to provide clear procedural guidance for customers.

## Refund Methods and Payment Types
Refunds will be issued to the original payment method where technically feasible.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)

    # 1. Headings get ContentRole.HEADING and is_canonical = False
    headings = [u for u in parsed.units if u.block_type == "heading"]
    assert len(headings) >= 2
    for h in headings:
        assert h.content_role == ContentRole.HEADING
        assert h.is_canonical is False

    # 2. Candidate discovery rejects structural headings
    for h in headings:
        is_cand, _, _ = CandidateDiscoveryEngine.is_candidate(h)
        assert is_cand is False

    # 3. CompletenessEvaluator knocks out heading subjects
    heading_cand = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_head",
        asset_id=env.asset_id,
        claim_text="How to Request a Refund",
        subject="How to Request a Refund",
        predicate="governs_policy_requirement",
        object_="Refund procedure",
        evidence_text_span="## How to Request a Refund",
        content_role=ContentRole.HEADING,
    )
    eval_head = CompletenessEvaluator.evaluate(heading_cand)
    assert eval_head.passed is False
    assert eval_head.details.get("decision_code") == DecisionCode.HEADING_NON_CANONICAL.value


# =========================================================================
# 5. Defect #10: Atomic Decomposition of Compound Eligibility Meta-Rules
# =========================================================================

@pytest.mark.asyncio
async def test_defect_10_compound_eligibility_meta_rule_decomposition(northwind_envelope_factory):
    """
    Defect #10: Compound meta-rule clauses ('all of the following conditions must be met')
    must be decomposed into 3 discrete atomic executable obligations.
    Verifies META_RULE_NOT_ATOMIC knockout gate against monolithic meta-rule claims.
    """
    content = """# Northwind Return Eligibility

In order to be eligible for a refund, all of the following conditions must be met:
1. The return must be initiated within the applicable return window.
2. The item must be in its original, undamaged condition with all tags and packaging intact.
3. A verifiable order number or proof of purchase must be provided.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    # Must contain 3 decomposed atomic claims
    predicates = {c.predicate for c in extracted_claims}
    assert "requires_return_within_applicable_window" in predicates
    assert "must_be_in_original_condition" in predicates
    assert "requires_verifiable_order_or_purchase_proof" in predicates

    # All 3 claims must be normative OBLIGATION
    for c in extracted_claims:
        if c.predicate in ("requires_return_within_applicable_window", "must_be_in_original_condition", "requires_verifiable_order_or_purchase_proof"):
            assert c.modality == "OBLIGATION"
            assert c.modal_operator == "must"
            eval_res = CompletenessEvaluator.evaluate(c)
            assert eval_res.passed is True

    # Monolithic meta-rule claim must be knocked out
    monolithic_cand = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_meta",
        asset_id=env.asset_id,
        claim_text="In order to be eligible for a refund, all of the following conditions must be met.",
        subject="Eligibility conditions",
        predicate="governs_policy_requirement",
        object_="all of the following conditions must be met",
        evidence_text_span="In order to be eligible for a refund, all of the following conditions must be met.",
    )
    eval_meta = CompletenessEvaluator.evaluate(monolithic_cand)
    assert eval_meta.passed is False
    assert eval_meta.details.get("decision_code") == DecisionCode.META_RULE_NOT_ATOMIC.value


# =========================================================================
# 6. Defects #20–#22: Cumulative Approval Thresholds & Fraud Review
# =========================================================================

@pytest.mark.asyncio
async def test_defects_20_22_cumulative_approval_thresholds_non_conflicting(northwind_envelope_factory):
    """
    Defects #20–#22: Approval thresholds (§4.2) must extract as cumulative approval tiers
    (tier_1_agent, tier_2_lead, customer_experience_manager, finance_director) + fraud review.
    Verifies that distinct authorization tiers evaluate as DISJOINT_APPROVAL_BANDS in CompatibilityGate.
    """
    content = """# Northwind Refund Authorizations

Refunds up to $100 may be approved by Tier 1 Customer Support Agents.
Refunds between $100.01 and $500 require approval from a Tier 2 Support Lead.
Refunds exceeding $500 require Customer Experience Manager approval.
Refunds exceeding $2,000 require approval from the Finance Director and must undergo secondary fraud review.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    approval_claims = [c for c in extracted_claims if c.predicate == "requires_approval_role"]
    assert len(approval_claims) == 4

    roles = {c.value for c in approval_claims}
    assert roles == {"tier_1_agent", "tier_2_lead", "customer_experience_manager", "finance_director"}

    # Fraud review claim for >$2000
    fraud_claim = next((c for c in extracted_claims if c.predicate == "requires_fraud_review"), None)
    assert fraud_claim is not None
    assert fraud_claim.value is True

    # CompatibilityGate: Tier 1 vs Tier 2 must evaluate as DISJOINT_APPROVAL_BANDS
    key_t1 = NormalizedClaimKey(subject_key="Refund", predicate_key="requires_approval_role", approval_band="up_to_100")
    key_t2 = NormalizedClaimKey(subject_key="Refund", predicate_key="requires_approval_role", approval_band="100_to_500")
    compat_res = CompatibilityGate.evaluate_applicability_overlap(key_t1, key_t2)
    assert compat_res.is_comparable is False
    assert compat_res.reason == "DISJOINT_APPROVAL_BANDS"


# =========================================================================
# 7. Defects #2, #3, #23: Weak Predicates Mapped to Canonical Registry
# =========================================================================

@pytest.mark.asyncio
async def test_weak_predicates_eliminated_from_canonical_registry(northwind_envelope_factory):
    """
    Defects #2, #3, #23: Raw verbs ('override', 'start', 'verify') must be mapped
    to domain-governed canonical predicates ('may_override_standard_terms', 'can_initiate_return',
    'must_verify_refund_conditions') and bare verbs knocked out by WEAK_PREDICATE.
    """
    content = """# Northwind Operational Rules

Business customers may override standard terms under negotiated agreements.
Customers can start their return online via the self-service portal.
Customer support must verify refund conditions prior to manual processing.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    predicates = {c.predicate for c in extracted_claims}
    assert "may_override_standard_terms" in predicates
    assert "can_initiate_return" in predicates
    assert "must_verify_refund_conditions" in predicates

    # Zero bare weak verbs produced
    for c in extracted_claims:
        assert c.predicate not in ("override", "start", "verify", "be", "defines", "specifies")

    # Synthetic weak verb claim is knocked out
    weak_cand = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_weak",
        asset_id=env.asset_id,
        claim_text="Business customers override standard terms.",
        subject="Business customers",
        predicate="override",
        object_="standard terms",
        evidence_text_span="Business customers override standard terms.",
    )
    eval_weak = CompletenessEvaluator.evaluate(weak_cand)
    assert eval_weak.passed is False
    assert eval_weak.details.get("decision_code") == DecisionCode.WEAK_PREDICATE.value


# =========================================================================
# 8. Boundary Ambiguity Routing: 'up to $50' vs 'under $50'
# =========================================================================

def test_boundary_ambiguity_routes_to_review():
    """
    Verifies that boundary ambiguity between 'up to $50' and 'under $50'
    is classified as GENUINE_BOUNDARY_AMBIGUITY and routed for human review.
    """
    key_a = NormalizedClaimKey(subject_key="Refund", predicate_key="has_refund_method", approval_band="up_to_50")
    key_b = NormalizedClaimKey(subject_key="Refund", predicate_key="has_refund_method", approval_band="under_50")

    compat = CompatibilityGate.evaluate_applicability_overlap(key_a, key_b)
    assert compat.is_comparable is True
    assert compat.reason == "GENUINE_BOUNDARY_AMBIGUITY"
    assert compat.relationship == "BOUNDARY_INCONSISTENCY"


# =========================================================================
# 9. Defect #37: Store Credit Definition & Validity Preservation (§2)
# =========================================================================

@pytest.mark.asyncio
async def test_defect_37_store_credit_definition_and_duration_preservation(northwind_envelope_factory):
    """
    Defect #37: Store Credit definition previously cut before duration ('valid for' missing '5 years.').
    Verifies that Section 2 Store Credit preserves the complete definition:
    - subject="Store Credit", predicate="has_definition"
    - validity={"duration": 5, "unit": "years"}
    - is_canonical=False, claim_type="definition"
    - CompletenessEvaluator passes intact claim
    - Synthetic truncated claim ('valid for') triggers INCOMPLETE_ASSERTION knockout gate
    """
    content = """# Northwind Refund Policy Handbook
## 2. Definitions
Store Credit: A balance issued to a customer account, redeemable online and in stores, valid for 5 years.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]
    assert len(units) >= 1

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    sc_claim = next((c for c in extracted_claims if "store credit" in c.subject.lower()), None)
    assert sc_claim is not None, "Store Credit definition claim must be extracted"
    assert sc_claim.predicate == "has_definition"
    assert sc_claim.claim_type == "definition"
    assert sc_claim.content_role == ContentRole.DEFINITION
    assert sc_claim.is_canonical is False
    assert "5 years" in sc_claim.claim_text or "5 years" in str(sc_claim.object)
    assert sc_claim.structured_values.get("validity") == {"duration": 5, "unit": "years"}

    # Complete claim passes CompletenessEvaluator
    eval_res = CompletenessEvaluator.evaluate(sc_claim)
    assert eval_res.passed is True

    # Truncated claim ending in dangling connective 'valid for' is knocked out
    truncated_claim = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_sc_trunc",
        asset_id=env.asset_id,
        claim_text="Store Credit: A balance issued to a customer account, redeemable online and in stores, valid for",
        subject="Store Credit",
        predicate="has_definition",
        object_="A balance issued to a customer account, redeemable online and in stores, valid for",
        evidence_text_span="Store Credit: A balance issued to a customer account, redeemable online and in stores, valid for",
    )
    eval_trunc = CompletenessEvaluator.evaluate(truncated_claim)
    assert eval_trunc.passed is False
    assert eval_trunc.details.get("decision_code") == DecisionCode.INCOMPLETE_ASSERTION.value


# =========================================================================
# 10. Defect #53: Case B Fragment Ending in 'with' Knocked Out (§20)
# =========================================================================

def test_defect_53_case_study_sentence_fragment_rejection(northwind_envelope_factory):
    """
    Defect #53: Sentence fragment from Case B ending in 'with'
    ('Northwind issued a free label and sent a replacement tent with')
    must be flagged with INCOMPLETE_ASSERTION and routed to REJECT.
    """
    env = northwind_envelope_factory("Dummy")
    frag_claim = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_case_frag",
        asset_id=env.asset_id,
        claim_text="Northwind issued a free label and sent a replacement tent with",
        subject="Northwind",
        predicate="issued",
        object_="a free label and sent a replacement tent with",
        evidence_text_span="Northwind issued a free label and sent a replacement tent with",
        content_role=ContentRole.EXAMPLE,
        is_canonical=False,
    )
    eval_res = CompletenessEvaluator.evaluate(frag_claim)
    assert eval_res.passed is False
    assert eval_res.details.get("decision_code") == DecisionCode.INCOMPLETE_ASSERTION.value

    decision = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate=frag_claim, envelope=env)
    assert decision.lifecycle_decision == ClaimLifecycleDecision.REJECT


# =========================================================================
# 11. Defect #55: Case B Narrative & Calendar Month Split Guard (§20)
# =========================================================================

@pytest.mark.asyncio
async def test_defect_55_case_b_narrative_and_digit_predicate_prevention(northwind_envelope_factory):
    """
    Defect #55: 'Daniel bought a $349 tent on May 1...' was incorrectly split on 'May'
    treating it as a modal verb and creating predicate='1'.
    Verifies that calendar month 'May' is shielded, no numeric predicate is created,
    content role is EXAMPLE, is_canonical=False, and EXAMPLE_NON_CANONICAL knocks it out.
    """
    content = """# Northwind Handbook
## 20. Revision History and Sample Case Studies
### Case B: Defective Merchandise Return
Daniel bought a $349 tent on May 1 and discovered a broken zipper on May 12.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    # Zero claims with numeric or single-char predicates
    for c in extracted_claims:
        assert not c.predicate.isdigit()
        assert len(c.predicate) > 1
        assert c.content_role == ContentRole.EXAMPLE
        assert c.is_canonical is False

    # Synthetic candidate with predicate='1' or from EXAMPLE must be rejected
    ex_cand = CandidateClaim.create(
        envelope_id=env.envelope_id,
        unit_id="u_case_b",
        asset_id=env.asset_id,
        claim_text="Daniel bought a $349 tent on May 1 and discovered a broken zipper on May 12.",
        subject="Daniel bought a $349 tent on",
        predicate="1",
        object_="and discovered a broken zipper on May 12",
        evidence_text_span="Daniel bought a $349 tent on May 1 and discovered a broken zipper on May 12.",
        content_role=ContentRole.EXAMPLE,
        is_canonical=False,
    )
    eval_ex = CompletenessEvaluator.evaluate(ex_cand)
    assert eval_ex.passed is False
    assert eval_ex.details.get("decision_code") in (
        DecisionCode.EXAMPLE_NON_CANONICAL.value,
        DecisionCode.WEAK_PREDICATE.value,
        DecisionCode.SUBJECT_NORMALIZATION_FAILED.value,
    )

    decision = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate=ex_cand, envelope=env)
    assert decision.lifecycle_decision == ClaimLifecycleDecision.REJECT


# =========================================================================
# 12. Defects #58–#64: Section 19 Contact Information Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_section_19_contact_information_isolated_from_policy_claims(northwind_envelope_factory):
    """
    Defects #58–#64: Contact information (phone, email, hours, address) from §19
    must be classified as CONTACT_INFO, is_canonical=False, claim_type=CONTACT_INFORMATION,
    and excluded from active policy conflicts.
    """
    content = """# Northwind Handbook
## 19. Contact Information and Escalation Channels
| Channel | Contact Details | Hours of Operation | Escalation SLA |
| Phone Support | 1-800-555-NORTH | Mon-Fri 8am-8pm EST | Tier 2 within 2 hours |
| Email Support | returns@northwind.com | 24/7 Intake | First response within 24 hours |
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type == "table_row"]
    assert len(units) >= 2

    for u in units:
        assert u.content_role == ContentRole.CONTACT_INFO
        assert u.is_canonical is False

    from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
    extracted_claims = []
    for u in units:
        extracted_claims.extend(DeterministicSchemaExtractor.extract_from_unit(u))

    assert len(extracted_claims) >= 2
    for c in extracted_claims:
        assert c.content_role == ContentRole.CONTACT_INFO
        assert c.is_canonical is False
        assert c.claim_type == "CONTACT_INFORMATION"
        assert c.predicate in (
            "has_contact_phone", "has_contact_email", "has_contact_address",
            "has_contact_hours", "has_service_level_target", "has_contact_channel",
        )

    # Excluded from conflict detection via non_canonical_types
    for c in extracted_claims:
        assert c.claim_type.lower() in ("contact_information", "contact_info")


# =========================================================================
# 13. Defects #49–#51: Section 4.2 Approval Thresholds Mapped to Roles
# =========================================================================

@pytest.mark.asyncio
async def test_section_4_2_approval_thresholds_predicate_and_structured_conditions(northwind_envelope_factory):
    """
    Defects #49–#51: Section 4.2 approval threshold bullets must extract:
    - predicate="requires_approval_role" or "requires_fraud_review"
    - value = role enum or boolean
    - structured conditions for refund_amount
    - must NOT fall back to predicate="has_definition"
    """
    content = """# Northwind Refund Policy
## 4. Refund Methods and Processing
### 4.2 Approval Thresholds
* $100.01 - $500: Tier 2 agent or team lead approval required.
* Over $500: Customer Experience Manager approval required.
* Over $2,000: Finance Director approval required and secondary fraud review.
"""
    env = northwind_envelope_factory(content)
    parsed = await DocumentParser.parse(env)
    units = [u for u in parsed.units if u.block_type in ("clause", "paragraph")]

    extracted_claims = []
    for u in units:
        extracted_claims.extend(DomainRuleExtractor.extract_from_unit(u))

    assert len(extracted_claims) >= 3
    for c in extracted_claims:
        assert c.predicate in ("requires_approval_role", "requires_fraud_review")
        assert c.predicate != "has_definition"
        assert c.subject == "Refund approval"
        assert any(cond.get("field") == "refund_amount" for cond in c.conditions)


# =========================================================================
# 14. Subject Normalizer: Conversational Preamble & Fragment Normalization
# =========================================================================

def test_subject_normalizer_and_anti_fragment_gate():
    """
    Verifies that SubjectNormalizer maps raw fragments to canonical entities,
    cleans unclosed parentheses, removes bullet characters, and flags conversational pronouns.
    """
    # 1. Unclosed parenthesis
    s1, ok1 = SubjectNormalizer.normalize("Business customers on standard accounts (custom contracts")
    assert ok1 is True
    assert s1 == "Business customer with standard account"

    # 2. Conversational fragment with pronoun prefix
    s2, ok2 = SubjectNormalizer.normalize("For damaged items valued under $40.00, we")
    assert ok2 is True
    assert s2 == "Damaged item valued under $40"

    # 3. Order number / proof of purchase
    s3, ok3 = SubjectNormalizer.normalize("The order number or proof of purchase")
    assert ok3 is True
    assert s3 == "Refund request"

    # 4. Bullet character cleaning
    cleaned = SubjectNormalizer.clean_raw_subject("\x7f•  Standard Return Window: ")
    assert cleaned == "Standard Return Window"

    # 5. Unresolved conversational pronoun prefix flags invalid
    s5, ok5 = SubjectNormalizer.normalize("We will then process the payment")
    assert ok5 is False

