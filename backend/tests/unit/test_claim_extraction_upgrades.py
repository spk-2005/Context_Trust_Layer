import pytest
from app.normalization.normalizer import DocumentNormalizer
from app.llm.mock_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_normalizer_scrub_noise():
    raw_content = (
        "Table of Contents\n"
        "Page 1 of 5\n"
        "Hello Team,\n"
        "Please note the following:\n"
        "Standard refund window is strictly limited to 14 days.\n"
        "All rights reserved.\n"
        "Copyright © 2026 Company Inc."
    )
    scrubbed = DocumentNormalizer.scrub_noise(raw_content)
    assert "Standard refund window is strictly limited to 14 days." in scrubbed
    assert "Table of Contents" not in scrubbed
    assert "Hello Team" not in scrubbed
    assert "All rights reserved" not in scrubbed
    assert "Copyright" not in scrubbed


@pytest.mark.asyncio
async def test_mock_provider_atomic_decomposition():
    provider = MockLLMProvider()
    doc_title = "Customer Agreement"
    sec_title = "Billing & Refunds"
    sec_content = (
        "Enterprise customers receive priority support and must submit refund requests within 14 days."
    )
    result = await provider.extract_claims(doc_title, sec_title, sec_content)
    claims = result.claims

    # Should decompose into at least 2 atomic claims
    assert len(claims) >= 2
    claim_texts = [c.claim_text for c in claims]
    assert any("receive priority support" in t for t in claim_texts)
    assert any("refund requests within 14 days" in t for t in claim_texts)

    # Check numeric extraction
    refund_claim = next((c for c in claims if "14 days" in c.claim_text), None)
    assert refund_claim is not None
    assert refund_claim.numeric_value == 14.0
    assert refund_claim.numeric_unit == "days"
    assert refund_claim.modality == "MUST"


@pytest.mark.asyncio
async def test_mock_provider_entity_anchoring_and_pronouns():
    provider = MockLLMProvider()
    doc_title = "SLA Agreement"
    sec_title = "Enterprise Tier"
    sec_content = "They can request account credits if monthly uptime falls below 99.9%."
    
    result = await provider.extract_claims(doc_title, sec_title, sec_content)
    assert len(result.claims) >= 1
    c = result.claims[0]
    
    # Pronoun "They" should be qualified with the anchor
    assert "Enterprise Tier" in c.subject or "SLA Agreement" in c.subject
    assert c.modality == "CAN"
    assert c.numeric_value == 99.9
    assert c.numeric_unit == "%"


@pytest.mark.asyncio
async def test_mock_provider_prohibition_modality():
    provider = MockLLMProvider()
    doc_title = "Acceptable Use Policy"
    sec_title = "General Rules"
    sec_content = "Users cannot share API tokens across multiple organizations."
    
    result = await provider.extract_claims(doc_title, sec_title, sec_content)
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.modality == "CANNOT"
