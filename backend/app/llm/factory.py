from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider


_provider_instance: BaseLLMProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get the configured LLM provider."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = (settings.llm_provider or "mock").lower()

    if provider_name == "openai" and settings.openai_api_key:
        from app.llm.openai_provider import OpenAIProvider
        _provider_instance = OpenAIProvider()
    else:
        _provider_instance = MockLLMProvider()

    return _provider_instance
