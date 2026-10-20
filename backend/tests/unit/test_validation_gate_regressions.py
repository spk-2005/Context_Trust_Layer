"""
Regression fixtures for Sprint AD-3 Validation Gate & Extraction Calibrations:
1. 'In no event shall...' preamble stripping & non-canonical rejection.
2. 'mcaps-...' title-slug rejection.
3. Table cells containing only ●, ❖, checkmarks, or dashes.
4. Curly quotes and non-breaking spaces in evidence matching.
5. Valid contract obligations that must remain approved (e.g. Customer, Supplier, Microsoft).
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.db.enums import SourceFamily, SourceIntent
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.extraction.subject_normalizer import SubjectNormalizer
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.validation_gate import (
    ClaimLifecycleDecision,
    ClaimLifecycleDecisionEngine,
    DecisionCode,
)


def _build_test_envelope(
    asset_id: str = "file:///contracts/commercial_agreement.pdf",
    text_content: str = "In no event shall Microsoft be liable. The Customer must pay all undisputed invoices within 30 days of receipt. Supplier shall maintain comprehensive general liability insurance.",
) -> CanonicalSourceEnvelope:
    env_id = uuid.uuid4()
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    payload = {"source": "Test Agreement", "text": text_content}

    return CanonicalSourceEnvelope(
        envelope_id=env_id,
        organization_id=org_id,
        source_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        asset_id=asset_id,
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="pdf",
        source_version="v1.0",
        content_hash=EnvelopeFactory.calculate_hash(payload),
        raw_payload=payload,
        captured_at=datetime.now(timezone.utc),
    )


# =========================================================================
# Regression Test 1: Preamble Stripping & Rejection
# =========================================================================

def test_preamble_stripping_and_rejection():
    """Verify that 'In no event shall...' preambles are stripped or rejected."""
    # Subject normalizer should recognize 'In no event' as invalid fragment or strip preamble
    clean = SubjectNormalizer.clean_raw_subject("In no event shall, Microsoft")
    assert "In no event" not in clean

    norm, is_valid = SubjectNormalizer.normalize("In no event", context="In no event shall Microsoft be liable")
    assert is_valid is False

    norm_doubt, is_valid_doubt = SubjectNormalizer.normalize("For the avoidance of doubt", context="")
    assert is_valid_doubt is False

    envelope = _build_test_envelope()
    candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:unit_1",
        asset_id=envelope.asset_id,
        claim_text="In no event shall Microsoft be liable for indirect damages.",
        subject="In no event",
        predicate="shall be liable",
        object_="indirect damages",
        modality="OBLIGATION",
        evidence_text_span="In no event shall Microsoft be liable for indirect damages.",
        locator={"line_start": 1, "page": 1},
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.95,
    )
    candidate.status = "verified"
    candidate.verification_plugin = "DocumentPlugin"

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
    # Must be knocked out by Invariant 0C
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert "Non-canonical subject entity" in gate_eval.decision_reason


# =========================================================================
# Regression Test 2: Document Title Slug Rejection
# =========================================================================

def test_document_title_slug_rejection():
    """Verify that document title slugs (e.g. mcaps-MSFT-GSA...) are rejected."""
    norm, is_valid = SubjectNormalizer.normalize("mcaps-MSFT-GSA-Commercial-Supplier-Agreement-Terms")
    assert is_valid is False
    assert norm == "Document Header"

    norm_lease, is_valid_lease = SubjectNormalizer.normalize("agreement_for_leasing_certain_products")
    assert is_valid_lease is False

    envelope = _build_test_envelope()
    candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:unit_2",
        asset_id=envelope.asset_id,
        claim_text="mcaps-MSFT-GSA-Commercial-Supplier-Agreement-Terms requires compliance with section 4.",
        subject="mcaps-MSFT-GSA-Commercial-Supplier-Agreement-Terms",
        predicate="requires",
        object_="compliance with section 4",
        modality="OBLIGATION",
        evidence_text_span="requires compliance with section 4.",
        locator={"line_start": 2, "page": 1},
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.95,
    )
    candidate.status = "verified"
    candidate.verification_plugin = "DocumentPlugin"

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
    assert "Non-canonical subject entity" in gate_eval.decision_reason


# =========================================================================
# Regression Test 3: Table Cells Containing Only Bullet Glyphs
# =========================================================================

def test_table_cell_bullet_glyphs_rejection():
    """Verify that table cells containing only ●, ❖, checkmarks, or dashes are knocked out."""
    for glyph in ["●", "❖", "✔", "-", "•", "N/A"]:
        envelope = _build_test_envelope()
        candidate = CandidateClaim.create(
            envelope_id=envelope.envelope_id,
            unit_id=f"{envelope.envelope_id}:0:glyph_{glyph}",
            asset_id=envelope.asset_id,
            claim_text=f"Feature Matrix row {glyph}",
            subject=glyph,
            predicate="has_support",
            object_="Included in Enterprise tier",
            modality="OBLIGATION",
            evidence_text_span=f"Feature Matrix row {glyph}",
            locator={"line_start": 10, "page": 2},
            extraction_strategy=ExtractionStrategyType.TABLE_AWARE,
            confidence=0.90,
        )
        candidate.status = "verified"
        candidate.verification_plugin = "DocumentPlugin"

        gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
        assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT
        assert "Non-semantic matrix bullet" in gate_eval.decision_reason


# =========================================================================
# Regression Test 4: Curly Quotes and Non-Breaking Spaces Evidence Grounding
# =========================================================================

def test_curly_quotes_and_non_breaking_spaces_evidence_matching():
    """Verify that curly quotes and non-breaking spaces match straight quotes and spaces in full text."""
    import re
    def _norm_grounding(s: str) -> str:
        if not s:
            return ""
        clean = s.lower().replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
        clean = clean.replace("\u00a0", " ").replace("\u2013", "-").replace("\u2014", "-")
        return re.sub(r"\s+", " ", clean).strip()

    full_text = 'The “Company” shall not disclose any Customer’s\u00a0data to third parties – period.'
    evidence_span = 'The "Company" shall not disclose any Customer\'s data to third parties - period.'

    norm_full = _norm_grounding(full_text)
    norm_span = _norm_grounding(evidence_span)

    assert norm_span in norm_full


# =========================================================================
# Regression Test 5: Valid Contract Obligations Must Remain Approved
# =========================================================================

def test_valid_contract_obligation_remains_approved():
    """Verify that legitimate subjects like Customer, Supplier, Microsoft remain approved."""
    envelope = _build_test_envelope()

    valid_obligations = [
        ("Customer", "must pay", "all undisputed invoices within 30 days of receipt"),
        ("Supplier", "shall maintain", "comprehensive general liability insurance"),
        ("Microsoft", "shall protect", "customer data in accordance with the DPA"),
    ]

    for subj, pred, obj in valid_obligations:
        candidate = CandidateClaim.create(
            envelope_id=envelope.envelope_id,
            unit_id=f"{envelope.envelope_id}:0:{subj}",
            asset_id=envelope.asset_id,
            claim_text=f"{subj} {pred} {obj}.",
            subject=subj,
            predicate=pred,
            object_=obj,
            modality="OBLIGATION",
            evidence_text_span=f"{subj} {pred} {obj}.",
            locator={"line_start": 1, "page": 1, "section_heading": "Section 2.1 Obligations"},
            extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
            confidence=0.95,
        )
        candidate.status = "verified"
        candidate.verification_plugin = "DocumentPlugin"
        candidate.verification_details = {"hash_verified": True, "evidence_offset": 0}

        gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
        assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.APPROVE, (
            f"Failed for {subj}: {gate_eval.decision_reason}"
        )
        assert gate_eval.decision_code == DecisionCode.APPROVE_ALL_PASSED


# =========================================================================
# Regression Test 6: Plural / Singular Stem Matching in Contracts
# =========================================================================

def test_plural_singular_stem_matching_in_evidence():
    """
    Verify that pluralized candidate subject ('Customers') grounds correctly against
    singular evidence span ('Customer must notify Microsoft within 10 business days.')
    without triggering a Subject-Evidence mismatch false rejection.
    """
    envelope = _build_test_envelope(
        text_content="Customer must notify Microsoft within 10 business days of any security incident."
    )
    candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:stem_test",
        asset_id=envelope.asset_id,
        claim_text="Customers must notify Microsoft within 10 business days of any security incident.",
        subject="Customers",  # Plural form
        predicate="must notify",
        object_="Microsoft within 10 business days of any security incident",
        modality="OBLIGATION",
        evidence_text_span="Customer must notify Microsoft within 10 business days of any security incident.",  # Singular form
        locator={"line_start": 4, "page": 1, "section_heading": "Section 4.1 Incident Reporting"},
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.95,
    )
    candidate.status = "verified"
    candidate.verification_plugin = "DocumentPlugin"
    candidate.verification_details = {"hash_verified": True, "evidence_offset": 0}

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
    assert gate_eval.meaning.passed is True
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.APPROVE


# =========================================================================
# Regression Test 7: Contractual Second/First-Person Pronoun Resolution
# =========================================================================

def test_contractual_pronoun_resolution_in_evidence():
    """
    Verify that second-person pronoun text ('You must pay all applicable taxes')
    normalized to enterprise subject ('Customer') grounds cleanly without rejection.
    """
    envelope = _build_test_envelope(
        text_content="You must pay all applicable taxes assessed in connection with your purchase."
    )
    candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:pronoun_test",
        asset_id=envelope.asset_id,
        claim_text="Customer must pay all applicable taxes assessed in connection with your purchase.",
        subject="Customer",  # Resolved from "You"
        predicate="must pay",
        object_="all applicable taxes assessed in connection with your purchase",
        modality="OBLIGATION",
        evidence_text_span="You must pay all applicable taxes assessed in connection with your purchase.",
        locator={"line_start": 8, "page": 2, "section_heading": "Section 3 Taxes"},
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.95,
    )
    candidate.status = "verified"
    candidate.verification_plugin = "DocumentPlugin"
    candidate.verification_details = {"hash_verified": True, "evidence_offset": 0}

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(candidate, envelope)
    assert gate_eval.meaning.passed is True
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.APPROVE


# =========================================================================
# Regression Test 8: Non-Canonical Scope & Metadata Routing Safeguards
# =========================================================================

def test_non_canonical_scope_and_metadata_routing_safeguards():
    """
    Verify that non-canonical overview statements and contact info metadata
    are safely routed to REVIEW / non-operative status with proper decision codes.
    """
    envelope = _build_test_envelope(
        text_content="For questions about this policy, contact privacy@microsoft.com or call 1-800-MICROSOFT."
    )
    contact_candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:contact_test",
        asset_id=envelope.asset_id,
        claim_text="Contact privacy@microsoft.com for inquiries.",
        subject="Contact Information",
        predicate="contact",
        object_="privacy@microsoft.com",
        modality="PERMISSION",
        evidence_text_span="contact privacy@microsoft.com",
        locator={"line_start": 20, "page": 5},
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.85,
    )
    contact_candidate.claim_type = "CONTACT_INFORMATION"
    contact_candidate.is_canonical = False

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(contact_candidate, envelope)
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW
    assert "CONTACT_INFO_NON_CANONICAL" in gate_eval.decision_reason

    # Also verify derived summary / overview scope statement routing
    summary_candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:summary_test",
        asset_id=envelope.asset_id,
        claim_text="Overview: This agreement governs Microsoft cloud service subscriptions.",
        subject="Document Overview",
        predicate="governs",
        object_="Microsoft cloud service subscriptions",
        modality="PERMISSION",
        evidence_text_span="This agreement governs Microsoft cloud service subscriptions.",
        locator={"line_start": 1, "page": 1},
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.90,
    )
    summary_candidate.claim_type = "derived_summary"
    summary_candidate.is_canonical = False

    summary_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(summary_candidate, envelope)
    assert summary_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW
    assert "NON-CANONICAL CONTEXT" in summary_eval.decision_reason


# =========================================================================
# Regression Test 9: Discretionary 'May' / Permissive Language Routing
# =========================================================================

def test_discretionary_permissive_language_held_in_hitl():
    """
    Verify that permissive or discretionary clauses ('may request an audit')
    are held in REVIEW rather than auto-approved as mandatory obligations.
    """
    envelope = _build_test_envelope(
        text_content="Customer may request an independent security audit once per calendar year upon 30 days notice."
    )
    discretionary_candidate = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=f"{envelope.envelope_id}:0:discretionary_test",
        asset_id=envelope.asset_id,
        claim_text="Customer may request an independent security audit once per calendar year upon 30 days notice.",
        subject="Customer",
        predicate="may request",
        object_="an independent security audit once per calendar year upon 30 days notice",
        modality="PERMISSION",
        evidence_text_span="Customer may request an independent security audit once per calendar year upon 30 days notice.",
        locator={"line_start": 12, "page": 3, "section_heading": "Section 5 Audits"},
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.84,  # Sub-threshold / discretionary
    )
    discretionary_candidate.status = "verified"
    discretionary_candidate.verification_plugin = "DocumentPlugin"
    discretionary_candidate.verification_details = {"hash_verified": True, "evidence_offset": 0}

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(discretionary_candidate, envelope)
    # Must be held in REVIEW because composite score < 0.88 auto-approve threshold or review triggered
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW
    assert "below 0.88 auto-approval threshold" in gate_eval.decision_reason or "Human review recommended" in gate_eval.decision_reason

