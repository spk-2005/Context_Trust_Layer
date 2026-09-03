"""Unit tests for OllamaProvider."""
import asyncio
import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def reset_provider():
    from app.llm.factory import reset_llm_provider
    reset_llm_provider()
    yield
    reset_llm_provider()


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:1.7b")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "qwen3:1.7b")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "30")
    from app.llm.ollama_provider import OllamaProvider
    return OllamaProvider()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chat_response(content: str):
    mock = AsyncMock()
    mock.status_code = 200
    mock.json.return_value = {"message": {"content": content}}
    mock.raise_for_status = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# _clean
# ---------------------------------------------------------------------------

def test_clean_strips_think_block():
    from app.llm.ollama_provider import OllamaProvider
    raw = "<think>internal reasoning here</think>\n{\"key\": 1}"
    assert OllamaProvider._clean(raw) == '{"key": 1}'


def test_clean_strips_fences():
    from app.llm.ollama_provider import OllamaProvider
    raw = "```json\n{\"key\": 1}\n```"
    assert OllamaProvider._clean(raw) == '{"key": 1}'


# ---------------------------------------------------------------------------
# extract_claims
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_claims_success(provider):
    claims_json = json.dumps({
        "claims": [{
            "claim_text": "All API endpoints must enforce TLS 1.3",
            "subject": "API endpoints",
            "predicate": "must enforce",
            "object": "TLS 1.3",
            "claim_type": "technical",
            "confidence": 0.97,
            "evidence_text_span": "All API endpoints must enforce TLS 1.3"
        }]
    })
    with patch.object(provider, "_chat", new=AsyncMock(return_value=claims_json)):
        result = await provider.extract_claims(
            document_title="Security Policy",
            section_title="Encryption",
            section_content="All API endpoints must enforce TLS 1.3",
        )
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.subject == "API endpoints"
    assert c.predicate == "must enforce"
    assert c.confidence == pytest.approx(0.97)
    assert result.extraction_model == "qwen3:1.7b"
    assert result.extraction_method == "ollama_json_extraction"


@pytest.mark.asyncio
async def test_extract_claims_empty_content(provider):
    result = await provider.extract_claims("doc", "section", "")
    assert result.claims == []


@pytest.mark.asyncio
async def test_extract_claims_bad_json_returns_empty(provider):
    with patch.object(provider, "_chat", new=AsyncMock(return_value="NOT JSON AT ALL")):
        result = await provider.extract_claims("doc", "section", "some content")
    assert result.claims == []


@pytest.mark.asyncio
async def test_extract_claims_network_error_returns_empty(provider):
    with patch.object(provider, "_chat", new=AsyncMock(side_effect=httpx.RequestError("timeout"))):
        result = await provider.extract_claims("doc", "section", "some content")
    assert result.claims == []


# ---------------------------------------------------------------------------
# get_embedding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_embedding_falls_back_to_hash_on_500(provider):
    """When Ollama returns 500 (qwen3 has no embedding endpoint), use hash fallback."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 500
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.llm.ollama_provider.httpx.AsyncClient", return_value=mock_client):
        emb = await provider.get_embedding("hello world")
    assert len(emb) == 1536
    assert abs(sum(v * v for v in emb) - 1.0) < 1e-6  # unit vector


@pytest.mark.asyncio
async def test_get_embedding_returns_native_when_available(provider):
    # httpx Response.json() is synchronous — use MagicMock not AsyncMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": [0.1] * 768}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.llm.ollama_provider.httpx.AsyncClient", return_value=mock_client):
        emb = await provider.get_embedding("hello")
    assert emb == [0.1] * 768


# ---------------------------------------------------------------------------
# evaluate_contradiction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_contradiction_detects(provider):
    contra_json = json.dumps({
        "is_contradiction": True,
        "conflict_type": "numerical_discrepancy",
        "severity": "high",
        "confidence": 0.93,
        "reasoning": "Claim A says 30 days but Claim B says 60 days."
    })
    with patch.object(provider, "_chat", new=AsyncMock(return_value=contra_json)):
        result = await provider.evaluate_contradiction(
            "Employees receive 30 days annual leave.",
            "Enterprise employees are granted 60 days annual leave.",
        )
    assert result.is_contradiction is True
    assert result.conflict_type == "numerical_discrepancy"
    assert result.severity == "high"
    assert result.confidence == pytest.approx(0.93)


@pytest.mark.asyncio
async def test_evaluate_contradiction_fallback_on_bad_json(provider):
    with patch.object(provider, "_chat", new=AsyncMock(return_value="oops not json")):
        result = await provider.evaluate_contradiction("a", "b")
    assert result.is_contradiction is False
    assert result.confidence > 0.0


# ---------------------------------------------------------------------------
# Factory integration
# ---------------------------------------------------------------------------

def test_factory_returns_ollama_provider():
    """OllamaProvider should be returned when LLM_PROVIDER=ollama in settings."""
    from app.llm import factory
    factory._provider_instance = None

    # Patch settings before the factory reads it
    with patch("app.llm.factory.settings") as mock_settings:
        mock_settings.llm_provider = "ollama"
        # Prevent OllamaProvider.__init__ from hitting real Ollama
        with patch("app.llm.ollama_provider.OllamaProvider.__init__", return_value=None):
            p = factory.get_llm_provider()

    from app.llm.ollama_provider import OllamaProvider
    assert isinstance(p, OllamaProvider)
    factory._provider_instance = None
