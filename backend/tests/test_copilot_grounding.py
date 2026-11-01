"""
Dedicated test suite for Copilot Evidence Grounding, Context Resolution, and Answer Verification.
"""

import pytest
from app.services.answer_verifier import AnswerVerifier
from app.services.context_resolver import ConversationContextResolver
from app.llm.mock_provider import MockLLMProvider


def test_answer_verifier_valid_citations():
    citations = [
        {
            "source_index": 1,
            "claim_text": "Enterprise refunds have a 30 days window.",
            "evidence": {"verbatim_quote": "Enterprise tier refunds must be initiated within 30 days."},
        },
        {
            "source_index": 2,
            "claim_text": "Refunds over $500 require VP authorization.",
            "evidence": {"verbatim_quote": "Amounts exceeding $500 require VP sign-off."},
        },
    ]

    answer = "Based on our policy [Source 1], enterprise refunds have a 30 days window. However, amounts above $500 require VP authorization [Source 2]."
    result = AnswerVerifier.verify(synthesized_answer=answer, citations=citations, has_conflicts=False)

    assert result.is_verified is True
    assert result.verification_status == "VERIFIED"
    assert result.cited_source_indices == [1, 2]
    assert result.invalid_source_indices == []
    assert len(result.unverified_numbers) == 0
    assert result.grounding_score >= 0.85


def test_answer_verifier_detects_hallucinated_citation():
    citations = [
        {
            "source_index": 1,
            "claim_text": "Port 22 is strictly closed by default.",
        }
    ]

    # LLM hallucinates [Source 7] which does not exist
    answer = "Port 22 is closed [Source 1], but overrides are granted on weekends [Source 7]."
    result = AnswerVerifier.verify(synthesized_answer=answer, citations=citations, has_conflicts=False)

    assert result.is_verified is False
    assert result.verification_status == "CITATION_MISMATCH"
    assert 7 in result.invalid_source_indices
    assert any("non-existent sources" in w for w in result.hallucination_warnings)


def test_answer_verifier_detects_unverified_financial_quantity():
    citations = [
        {
            "source_index": 1,
            "claim_text": "Standard refund cap is $500 without managerial review.",
            "evidence": {"verbatim_quote": "Claims up to $500 can be processed by Tier 1."},
        }
    ]

    # LLM asserts a fabricated figure "$75,000" and "90 days" not present in evidence
    answer = "Tier 1 agents may issue refunds up to $75,000 within 90 days [Source 1]."
    result = AnswerVerifier.verify(synthesized_answer=answer, citations=citations, has_conflicts=False)

    assert len(result.unverified_numbers) > 0
    assert any("$75,000" in n or "75,000" in n for n in result.unverified_numbers)
    assert result.verification_status in ["PARTIALLY_GROUNDED", "UNVERIFIED"]


def test_answer_verifier_flags_omitted_conflicts():
    citations = [
        {
            "source_index": 1,
            "claim_text": "Direct SSH access is permitted with bastion approval.",
        }
    ]

    # has_conflicts is True, but answer presents an uncritical "Yes, direct SSH is fully permitted" without caveat
    answer = "Yes, direct SSH access is permitted whenever you request bastion approval [Source 1]."
    result = AnswerVerifier.verify(synthesized_answer=answer, citations=citations, has_conflicts=True)

    assert result.disputed_conflict_flagged is False
    assert any("conflict" in w.lower() for w in result.hallucination_warnings)
    assert result.grounding_score < 1.0


@pytest.mark.anyio
async def test_context_resolver_multi_turn_expansion():
    mock_llm = MockLLMProvider()
    resolver = ConversationContextResolver(mock_llm)

    history = [
        {"role": "user", "content": "What is the return window for enterprise contracts?"},
        {"role": "assistant", "content": "Enterprise contracts specify a 30-day window [Source 1]."},
    ]

    # Follow-up query with pronoun / continuation
    follow_up = "Does that apply to custom tiers as well?"
    resolved = await resolver.resolve_query(follow_up, history)

    # Context resolver should retain key anchor terms from previous turn
    assert ("enterprise" in resolved.lower() or "return window" in resolved.lower() or "custom tiers" in resolved.lower())
