import json
import pytest
import httpx
from unittest.mock import MagicMock, patch
from app.llm.ollama_provider import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_structured_extraction():
    provider = OllamaProvider()

    claims_json = json.dumps({
        "claims": [
            {
                "claim_text": "All privileged accounts must use multi-factor authentication.",
                "subject": "Privileged accounts",
                "predicate": "must use",
                "object": "multi-factor authentication",
                "modality": "MUST",
                "claim_type": "security",
                "evidence_text": "All privileged accounts must use multi-factor authentication.",
                "confidence": 0.98,
                "numeric_value": None,
                "numeric_unit": None
            },
            {
                "claim_text": "Passwords must be at least 14 characters long.",
                "subject": "Passwords",
                "predicate": "must be at least",
                "object": "14 characters long",
                "modality": "MUST",
                "claim_type": "security",
                "evidence_text": "Passwords must be at least 14 characters long.",
                "confidence": 0.95,
                "numeric_value": 14.0,
                "numeric_unit": "characters"
            }
        ]
    })

    with patch.object(provider, "_chat", return_value=claims_json):
        result = await provider.extract_claims(
            document_title="Security Mandate",
            section_title="Access Controls",
            section_content="All privileged accounts must use multi-factor authentication. Passwords must be at least 14 characters long."
        )

        assert len(result.claims) == 2
        assert result.claims[0].subject == "Privileged accounts"
        assert result.claims[0].modality == "MUST"
        assert result.claims[1].numeric_value == 14.0
        assert result.claims[1].numeric_unit == "characters"


@pytest.mark.asyncio
async def test_ollama_provider_network_fallback():
    provider = OllamaProvider()

    with patch.object(provider, "_chat", side_effect=httpx.RequestError("timeout")):
        result = await provider.extract_claims(
            document_title="Test Document",
            section_title="General",
            section_content="Some content"
        )
        assert result.claims == []
