"""
Permanent Regression Test Suite: AD-4 Staged Ingestion Guardrails.
Verifies failure pattern eradications, regulatory actor head-noun normalization,
and false-negative protections across enterprise compliance and legal contracts.
"""

from __future__ import annotations

import uuid
import pytest

from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit, ContentRole


def _create_unit(text: str, role: ContentRole = ContentRole.POLICY_RULE) -> ParsedEvidenceUnit:
    return ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test_doc",
        block_type="clause",
        content_text=text,
    )


@pytest.mark.fast
def test_phantom_governance_policy_suppressed():
    """Verify that compliance text lacking 'governance policy' in evidence never receives synthetic 'Governance Policy'."""
    text = "The Service Trust Portal provides independently audited compliance reports."
    unit = _create_unit(text)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    for c in claims:
        assert c.subject != "Governance Policy", "Synthetic ungrounded 'Governance Policy' must never be emitted"


@pytest.mark.fast
def test_bare_pronoun_subject_rejected():
    """Verify bare pronoun phrases ('Then, they', 'It', 'This') are rejected from being claim subjects."""
    text = "Then, they follow internal guidelines."
    unit = _create_unit(text)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    for c in claims:
        assert c.subject.lower().strip() not in ("then, they", "they", "it", "this", "that"), (
            f"Bare pronoun subject '{c.subject}' should have been rejected"
        )


@pytest.mark.fast
def test_non_normative_narrative_fragment_rejected():
    """Verify concatenated section headings glued to descriptive narrative paragraphs are rejected."""
    text = (
        "Audits, reports, and certificates HDS certification imposes advanced security "
        "and privacy requirements on hosting services and cloud providers to ensure that "
        "the confidentiality and integrity of sensitive data that must be located within "
        "the EEA is adequately protected."
    )
    unit = _create_unit(text)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    # The run-on narrative preamble must not be emitted as an atomic subject
    for c in claims:
        assert len(c.subject.split()) <= 10, f"Subject too long: '{c.subject}'"
        assert not c.subject.lower().startswith("audits, reports, and certificates"), (
            "Concatenated heading must not become subject"
        )


@pytest.mark.fast
def test_regulatory_actor_head_noun_preserved():
    """Verify legitimate regulatory subjects with relative clauses ('Covered entities that...') are preserved with clean head-noun."""
    text = (
        "Covered entities that create, receive, maintain, or transmit protected health information "
        "must enter into business associate agreements with their service providers."
    )
    unit = _create_unit(text)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1, "Legitimate regulatory rule must not be suppressed"
    c = claims[0]
    assert c.subject == "Covered entities", f"Expected normalized actor head-noun, got '{c.subject}'"
    assert c.modality == "OBLIGATION"
    assert any("create, receive, maintain, or transmit" in cond for cond in c.conditions), (
        f"Relative clause must be preserved in conditions: {c.conditions}"
    )


@pytest.mark.fast
def test_subordinate_clause_condition_rescued():
    """Verify introductory subordinate clauses ('Because we offer X, we must...') are extracted to conditions."""
    text = (
        "Because we offer hyperscale, multitenant services that are standardized for all our customers, "
        "we must operate in a consistent manner."
    )
    unit = _create_unit(text)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1, "Normative rule with subordinate clause must be extracted"
    c = claims[0]
    assert c.subject in ("Company", "Microsoft", "we"), f"Expected Company subject, got '{c.subject}'"
    assert c.modality == "OBLIGATION"
    assert any("hyperscale" in cond.lower() for cond in c.conditions), (
        f"Subordinate clause must be extracted into conditions: {c.conditions}"
    )


@pytest.mark.fast
def test_table_header_subject_rejected():
    """Verify table column headers and grid labels are rejected as claim subjects."""
    text = "Col0 must be submitted on time."
    unit = _create_unit(text)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    for c in claims:
        assert not c.subject.lower().startswith("col0"), "Table column label must not be subject"


@pytest.mark.fast
def test_conditional_exception_retained():
    """Verify exception clauses ('Unless otherwise agreed in writing, Vendor must...') retain explicit condition."""
    text = "Unless otherwise agreed in writing, Vendor must deliver the goods within 30 days."
    unit = _create_unit(text)
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    c = claims[0]
    assert c.subject == "Vendor"
    assert c.modality == "OBLIGATION"
    assert any("otherwise agreed" in cond.lower() for cond in c.conditions), (
        f"Condition must be captured in claim conditions: {c.conditions}"
    )
