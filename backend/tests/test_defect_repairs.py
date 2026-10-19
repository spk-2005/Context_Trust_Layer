"""
Regression Tests for Demonstrated Extraction Defect Repairs.

Each demonstrated defect requires both:
1. Negative example: Proves the known mistake is prevented.
2. Positive example: Proves legitimate rules still survive.
"""

import uuid
import pytest

from app.conflict_engine.normalizer import ClaimNormalizer
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.deontic_classifier import DeonticClassifier
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


def make_test_unit(text: str, role: ContentRole = ContentRole.POLICY_RULE, hier: list = None) -> ParsedEvidenceUnit:
    return ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id=f"test-{uuid.uuid4().hex[:6]}",
        block_type="clause",
        content_text=text,
        content_role=role,
        hierarchical_context=hier or ["EPCS Section"],
        locator={"line_start": 1, "line_end": 2, "page_number": 1},
    )


# =========================================================================
# Defect 1: "Administration" agency name triggers an administration fee
# =========================================================================

def test_defect_1_negative_dea_agency_does_not_trigger_fee():
    """Negative example: DEA agency name must never trigger may_apply_administration_fee."""
    sentence = (
        "The US Drug Enforcement Administration (DEA) Electronic Prescriptions for "
        "Controlled Substances (EPCS) is a rule that went into effect on 1 June 2010."
    )
    unit = make_test_unit(sentence)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    fee_claims = [c for c in claims if "fee" in c.predicate.lower() or "fee" in str(c.object).lower()]
    assert len(fee_claims) == 0, f"Spurious fee claim created from DEA agency mention: {fee_claims}"


def test_defect_1_positive_legitimate_administration_fee_survives():
    """Positive example: Legitimate dispute administration fee statement must be extracted."""
    sentence = "A $15 administration fee may apply for fraudulent claims."
    unit = make_test_unit(sentence)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    fee_claims = [c for c in claims if "administration_fee" in c.predicate.lower()]
    assert len(fee_claims) >= 1, "Legitimate administration fee was not extracted"
    assert fee_claims[0].predicate == "may_apply_administration_fee"


# =========================================================================
# Defect 2: Adverbs ("also", "digitally") become the predicate
# =========================================================================

def test_defect_2_negative_adverbs_not_predicates():
    """Negative example: Adverbs like 'also' or 'digitally' must never be the bare predicate."""
    s1 = "Prescribers can digitally sign prescriptions."
    unit1 = make_test_unit(s1)
    claims1 = DomainRuleExtractor.extract_from_unit(unit1)
    for c in claims1:
        assert c.predicate.lower() != "digitally", "Bare adverb 'digitally' was extracted as predicate"
        assert c.predicate.lower() != "also", "Bare adverb 'also' was extracted as predicate"
        assert "sign" in c.predicate.lower(), f"Operative verb was not captured in predicate: {c.predicate}"

    s2 = "You can also provide secondary verification."
    unit2 = make_test_unit(s2)
    claims2 = DomainRuleExtractor.extract_from_unit(unit2)
    for c in claims2:
        assert c.predicate.lower() != "also", "Bare adverb 'also' was extracted as predicate"
        assert c.predicate.lower() == "provide", f"Expected operative verb 'provide', got: {c.predicate}"


def test_defect_2_positive_operative_actions_preserved():
    """Positive example: Operative predicates are properly extracted and normalized."""
    sentence = "With the Microsoft Authenticator app, you can provide secondary verification for MFA scenarios."
    unit = make_test_unit(sentence)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    c = claims[0]
    assert c.predicate == "provide"
    assert c.subject == "Users"


# =========================================================================
# Defect 3: Document title as subject & Pronoun resolution
# =========================================================================

def test_defect_3_negative_document_title_not_subject_of_unrelated_sentences():
    """Negative example: Document title must not become subject with fallback has_validity_rule."""
    sentence = "EPCS is a rule that went into effect on 1 June 2010."
    unit = make_test_unit(
        sentence,
        hier=["Electronic Prescriptions for Controlled Substances (EPCS)"],
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    validity_claims = [c for c in claims if c.predicate == "has_validity_rule"]
    assert len(validity_claims) == 0, "Document title assigned as subject of non-validity sentence"


def test_defect_3_positive_pronoun_antecedent_resolved():
    """Positive example: Pronoun 'it' is correctly resolved to 'Hard token'."""
    sentence = "If a hard token is used, it must meet FIPS 140 Security Level 1 for cryptographic devices or OTP devices."
    unit = make_test_unit(sentence)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    c = claims[0]
    assert c.subject == "Hard token"
    assert "it" != c.subject.lower()


# =========================================================================
# Defect 4: Several actions become one atomic claim
# =========================================================================

def test_defect_4_positive_coordinated_multi_action_split():
    """Positive example: Coordinated multi-action clauses are decomposed into atomic claims."""
    sentence = (
        "Two-factor authentication must be used to assign a prescriber within the electronic system, "
        "approve a prescription entry, and digitally sign a prescription."
    )
    unit = make_test_unit(sentence)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 3, f"Expected 3 atomic claims from coordinated 2FA sentence, got {len(claims)}"
    subjects = {c.subject for c in claims}
    assert "Electronic system prescriber assignment" in subjects
    assert "Prescription entry approval" in subjects
    assert "Prescription digital signing" in subjects


def test_defect_4_positive_coordinated_multi_actor_split():
    """Positive example: Prescribers and Pharmacies actions split cleanly."""
    sentence = (
        "Prescribers can digitally sign, transmit, report, and archive electronic prescriptions, "
        "while pharmacies can receive, dispense, and archive these electronic prescriptions."
    )
    unit = make_test_unit(sentence)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 3, f"Expected 3 atomic claims, got {len(claims)}"
    actors = {c.subject for c in claims}
    assert "Prescribers" in actors
    assert "Pharmacies" in actors


# =========================================================================
# Defect 5: "See documentation" becomes a policy rule
# =========================================================================

def test_defect_5_negative_reference_citation_excluded_from_claims():
    """Negative example: Reference citation must be classified as citation and excluded from rules."""
    text = "For more information, see Title 21 Code of Federal Regulations Part 1311.115 Additional requirements for two-factor authentication."
    role = DocumentParser._classify_content_role(text, ["EPCS Overview"], "paragraph")
    assert role == ContentRole.REFERENCE_CITATION, f"Expected REFERENCE_CITATION, got {role}"
    unit = make_test_unit(text, role=role)
    eligible, _, _ = CandidateDiscoveryEngine.is_candidate(unit)
    assert not eligible, "Reference citation was incorrectly marked candidate-eligible for claim extraction"


def test_defect_5_positive_normative_rule_survives():
    """Positive example: Genuine normative policy rule survives candidate discovery."""
    text = "Verifiers at AAL3 shall be validated at FIPS 140 Level 1 or higher."
    unit = make_test_unit(text)
    eligible, _, _ = CandidateDiscoveryEngine.is_candidate(unit)
    assert eligible, "Genuine normative obligation was incorrectly filtered"
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    assert claims[0].subject == "Verifiers at AAL3"
    assert claims[0].modality == "OBLIGATION"


# =========================================================================
# Defect 6: Regulation numbers become conflicting values
# =========================================================================

def test_defect_6_negative_regulation_citations_masked_from_quantity_parsing():
    """Negative example: Citations like 'Title 21' or 'NIST SP 800-63B' must not be parsed as quantities."""
    test_citations = [
        "Title 21 Code of Federal Regulations Part 1311.115",
        "NIST SP 800-63B Section 4.3",
        "FIPS 140 Security Level 1",
        "FIPS 140 Level 2",
    ]
    for citation in test_citations:
        scalar, unit = ClaimNormalizer.extract_scalar_and_unit(citation, "")
        assert scalar is None and unit is None, f"Spurious quantity extracted from citation '{citation}': ({scalar}, {unit})"


def test_defect_6_positive_legitimate_scalar_values_extracted():
    """Positive example: Legitimate policy durations and currency values are parsed correctly."""
    scalar, unit = ClaimNormalizer.extract_scalar_and_unit("must be submitted within 30 days", "")
    assert scalar == 30.0
    assert unit == "days"

    scalar_m, unit_m = ClaimNormalizer.extract_scalar_and_unit("an administration fee of $15 may apply", "")
    assert scalar_m == 15.0
    assert unit_m == "USD"
