import pytest
from app.llm.openai_provider import OpenAIProvider
from app.llm.factory import get_llm_provider, reset_llm_provider
from app.core.config import settings


def test_openrouter_provider_instantiation():
    provider = OpenAIProvider(
        api_key="sk-or-test-key",
        base_url="https://openrouter.ai/api/v1",
        model="z-ai/glm-5.3-flash",
    )
    assert provider.model == "z-ai/glm-5.3-flash"
    assert provider.base_url == "https://openrouter.ai/api/v1"
    assert provider.api_key == "sk-or-test-key"


def test_factory_returns_openrouter_provider(monkeypatch):
    reset_llm_provider()
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-or-test-key")
    monkeypatch.setattr(settings, "openrouter_model", "z-ai/glm-5.3-flash")
    monkeypatch.setattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1")

    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "z-ai/glm-5.3-flash"
    assert provider.base_url == "https://openrouter.ai/api/v1"
    reset_llm_provider()
