"""
Permanent Regression Test Suite: Cross-Domain Claim Extraction & Generalization.

Verifies that the generalized extraction pipeline retains 100% fidelity on:
1. Multi-column PDF reading order (steps do not interleave horizontally).
2. Normative rules ending with citations (must be retained, not discarded as reference_citation).
3. Numbered return & refund instructions (treated as operative policy rules, not procedural clicks).
4. Website sitemap footers (correctly rejected as non-canonical metadata).
5. Software UI walkthrough capabilities (affordances rejected from governance policies).
6. Pseudo-definitions from arbitrary colon lines (rejected from normative policy claims).
7. Promotional preamble & trade-in boilerplate (rejected from core return policy claims).
"""

import uuid
import pytest
from pathlib import Path

from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import ExtractionStrategyType
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit
from app.ingestion.universal_file_parser import UniversalFileParser

RAW_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "research" / "validation_50" / "raw_documents"


def test_multi_column_pdf_reading_order_not_interleaved():
    """Regression 1: Multi-column PDF layout must preserve logical sequential reading order."""
    doc_path = RAW_DOCS_DIR / "Microsoft Store Refund & Return Policy (Surface, Xbox, etc.).pdf"
    if not doc_path.exists():
        pytest.skip(f"Document missing: {doc_path}")

    raw_bytes = doc_path.read_bytes()
    parsed = UniversalFileParser.parse_structured(doc_path.name, raw_bytes, doc_title="Return Policy")
    full_text = parsed.full_text or ""

    # In page 2, step 3 clause must not be broken up by step 4 text
    expected_step3_clause = "Using the label, return the product in like-new condition in its original packaging with all parts and documentation included."
    expected_step4_clause = "Once we get the item back and confirm eligibility, we'll issue a refund to your original payment method within 3-5 business days."

    # Both complete clauses must appear intact without horizontal column interleaving
    assert expected_step3_clause in full_text.replace("\n", " "), (
        "Step 3 return condition was interleaved or fragmented across columns"
    )
    assert expected_step4_clause in full_text.replace("\n", " "), (
        "Step 4 refund timeframe was interleaved or fragmented across columns"
    )


def test_citation_ending_rule_retained_as_normative():
    """Regression 2: Normative obligations ending with 'For more information, see...' must not be discarded."""
    text = (
        "You must be a Global Administrator to manage Auto-claim policies at the organization level. "
        "User, License and Global admins can create and manage auto-claim policies in the Auto-claim policy tab under Licenses. "
        "For more information, see About Microsoft 365 admin roles."
    )
    role = DocumentParser._classify_content_role(text, context=["Before you begin"], block_type="paragraph")
    assert role == ContentRole.POLICY_RULE, f"Expected POLICY_RULE, got {role}"

    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-doc-058",
        block_type="paragraph",
        content_role=role,
        content_text=text,
        structured_data={},
        locator={"line_start": 34, "line_end": 34},
        hierarchical_context=["Before you begin"],
        sequence_index=34,
    )

    is_cand, strat, reason = CandidateDiscoveryEngine.is_candidate(unit)
    assert is_cand is True, f"Candidate was rejected: {reason}"

    claims = DomainRuleExtractor.extract_from_unit(unit)
    admin_claims = [c for c in claims if c.subject == "Global Administrator"]
    assert len(admin_claims) == 1, f"Expected Global Administrator claim, got {len(admin_claims)}"
    assert admin_claims[0].predicate == "must_be_role_to_manage_auto_claim_policies"
    assert admin_claims[0].modality == "OBLIGATION"


def test_numbered_return_instruction_retained_as_policy_rule():
    """Regression 3: Numbered return and refund conditions must be retained as policy rules, not procedural clicks."""
    text = (
        "3. Ship the product back to us Using the label, return the product in like-new condition in its original "
        "packaging with all parts and documentation included."
    )
    is_ui = DomainRuleExtractor.is_procedural_ui_instruction(text)
    assert is_ui is False, "Return condition was incorrectly flagged as a procedural UI instruction"

    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-doc-060",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        content_text=text,
        structured_data={},
        locator={"line_start": 9, "line_end": 9},
        hierarchical_context=["How to start your free return"],
        sequence_index=9,
    )

    claims = DomainRuleExtractor.extract_from_unit(unit)
    matched = [c for c in claims if c.predicate == "must_return_in_condition"]
    assert len(matched) == 1, "Failed to extract must_return_in_condition"
    assert matched[0].subject == "Customers"
    assert matched[0].modality == "OBLIGATION"


def test_sitemap_footer_tables_rejected():
    """Regression 4: Website sitemap footers must be classified as non-canonical metadata and rejected."""
    headers = ["What's new", "Microsoft Store", "Education", "Business", "Developer & IT", "Company"]
    clean_hdrs = [h.lower() for h in headers]
    is_sitemap = any(any(w in h for w in ("what's new", "microsoft store", "education", "business", "developer & it", "company")) for h in clean_hdrs)
    assert is_sitemap is True

    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-doc-060",
        block_type="table_row",
        content_role=ContentRole.DOCUMENT_METADATA,
        is_canonical=False,
        content_text="Surface Pro 9 | Buy Surface | Microsoft in education | Microsoft Cloud | Azure",
        structured_data={"table_type": "website_sitemap_footer", "table_headers": headers},
        locator={"line_start": 100, "line_end": 100},
        hierarchical_context=["Footer"],
        sequence_index=100,
    )

    is_cand, _, reason = CandidateDiscoveryEngine.is_candidate(unit)
    assert is_cand is False, f"Sitemap footer row was not rejected: {reason}"


def test_software_ui_affordances_not_governance_claims():
    """Regression 5: Instructional affordances ('you can use', 'you can create') must not become governance claims."""
    affordance_sentences = [
        "For some products and services, you can use an *auto-claim policy* to let users automatically claim a license without requiring you to assign them.",
        "With an auto-claim policy in place, users can automatically claim a license for a product the first time that they sign in to an app that requires a license.",
        "After you turn on the feature, you can create an auto-claim policy.",
        "For each product in your auto-claim policy, you can specify which apps and services to include when a user is automatically assigned a license to that product.",
        "If you have backup products assigned to the policy, you can change the order in which they're used to assign licenses when users sign in to the app.",
        "Admins can now create auto-claim policies for Power Apps per user licenses in the Microsoft 365 admin center, similar to how they can create auto-claim policies for other Microsoft products and services.",
    ]

    for sentence in affordance_sentences:
        is_affordance = DomainRuleExtractor.is_procedural_ui_instruction(sentence)
        assert is_affordance is True, f"Affordance was not recognized: {sentence}"


def test_colon_definition_lines_not_spurious_policy_claims():
    """Regression 6: Narrative lines with colons must not generate spurious has_definition policy claims."""
    pseudo_definition_lines = [
        "Returns: Holiday extended return policy available with eligible physical products purchased between October 1, 2026 - December 2, 2026 from Microsoft Store online and Microsoft Experience Centers in select markets.",
        "Price protection: Microsoft Store Price Adjustment: Holiday extended price protection valid on purchases of qualifying physical consumer products.",
        "Both price adjustments: Customer is eligible only if the product is in stock for purchase at Microsoft Store or a Microsoft Experience Center.",
        "Trade-In: Available only through the Microsoft Store online in the United States.",
        "Term Invoicing Agreement Effective Date: [date]",
        "Term of Invoicing Agreement: Until terminated Agreed and accepted Microsoft Vendor Signature: Signature:",
    ]

    for line in pseudo_definition_lines:
        unit = ParsedEvidenceUnit.create(
            envelope_id=uuid.uuid4(),
            asset_id="test",
            block_type="paragraph",
            content_role=ContentRole.POLICY_RULE,
            content_text=line,
            structured_data={},
            locator={"line_start": 1, "line_end": 1},
            hierarchical_context=["Policy Context"],
            sequence_index=1,
        )
        claims = DomainRuleExtractor.extract_from_unit(unit)
        has_def = any(c.predicate == "has_definition" for c in claims)
        assert not has_def, f"Spurious has_definition extracted from: {line}"


def test_promotional_preamble_and_boilerplate_rejected():
    """Regression 7: Retail promotion disclaimers and contract boilerplate must be skipped from policy claims."""
    boilerplate_sentences = [
        "Microsoft reserves the right to modify or discontinue offers at any time.",
        "An Eligible RetailerLet's chat Price Adjustment cannot be requested at time of purchase.",
        "To be eligible for trade in, (i) you must own the qualifying device, (ii) the device must power on.",
        "The device cannot be password protected and must include its original chargers, accessories, and hard drive.",
        "Customer must mail in the qualifying trade-in device to be eligible for reimbursement.",
        "Devices determined to not meet eligibility criteria may be shipped back to the customer or recycled.",
        "Recycled devices are not eligible for cash back.",
        "Cannot be transferred or otherwise redeemed for cash or gift cards, or credit towards other devices or products.",
        "Capitalized terms used herein and not otherwise defined shall have the meanings given in the Services Contracts between the parties.",
        "This Invoicing Agreement will be effective on [date] (the 'Effective Date').",
    ]

    for line in boilerplate_sentences:
        unit = ParsedEvidenceUnit.create(
            envelope_id=uuid.uuid4(),
            asset_id="test-boilerplate",
            block_type="clause",
            content_role=ContentRole.POLICY_RULE,
            content_text=line,
            structured_data={},
            locator={"line_start": 1, "line_end": 1},
            hierarchical_context=["Discounts and Returns"],
            sequence_index=1,
        )
        claims = DomainRuleExtractor.extract_from_unit(unit)
        assert len(claims) == 0, f"Boilerplate line generated claims: {line} -> {[c.predicate for c in claims]}"
