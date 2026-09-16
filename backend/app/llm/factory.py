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

    if provider_name in ("openrouter", "ox-alpha", "ox_alpha", "oxalpha"):
        api_key = settings.openrouter_api_key or settings.openai_api_key
        if api_key:
            from app.llm.openai_provider import OpenAIProvider
            _provider_instance = OpenAIProvider(
                api_key=api_key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model,
                embedding_model=settings.openrouter_embedding_model,
                default_headers={
                    "HTTP-Referer": "https://contexttrustlayer.ai",
                    "X-Title": "Context Trust Layer",
                },
            )
        else:
            import logging
            logging.getLogger(__name__).warning(
                "OpenRouter API key is not configured; falling back to MockLLMProvider."
            )
            _provider_instance = MockLLMProvider()
    elif provider_name == "openai" and settings.openai_api_key:
        from app.llm.openai_provider import OpenAIProvider
        _provider_instance = OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            embedding_model=settings.openai_embedding_model,
        )
    elif provider_name == "ollama":
        from app.llm.ollama_provider import OllamaProvider
        _provider_instance = OllamaProvider()
    else:
        if provider_name not in ("mock",):
            import logging
            logging.getLogger(__name__).warning(
                "Unknown or unconfigured LLM provider '%s'; falling back to MockLLMProvider.",
                provider_name,
            )
        _provider_instance = MockLLMProvider()

    return _provider_instance


def reset_llm_provider() -> None:
    """Reset the cached provider (useful in tests)."""
    global _provider_instance
    _provider_instance = None
