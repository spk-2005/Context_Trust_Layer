import logging
from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider

logger = logging.getLogger(__name__)

_provider_instance: BaseLLMProvider | None = None


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Factory function to get or instantiate the configured LLM provider."""
    global _provider_instance

    target_provider = (provider_name or settings.llm_provider or "mock").lower().strip()

    # If no override and cached instance matches target, return cached
    if provider_name is None and _provider_instance is not None:
        return _provider_instance

    if target_provider in ("openrouter", "ox-alpha", "ox_alpha", "oxalpha"):
        api_key = settings.openrouter_api_key or settings.openai_api_key
        if api_key:
            from app.llm.openai_provider import OpenAIProvider
            instance = OpenAIProvider(
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
            logger.warning("OpenRouter API key is not configured; falling back to MockLLMProvider.")
            instance = MockLLMProvider()
    elif target_provider == "openai" and settings.openai_api_key:
        from app.llm.openai_provider import OpenAIProvider
        instance = OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            embedding_model=settings.openai_embedding_model,
        )
    elif target_provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider
        instance = OllamaProvider()
    else:
        if target_provider not in ("mock", "rule_engine"):
            logger.warning(
                "Unknown or unconfigured LLM provider '%s'; falling back to MockLLMProvider.",
                target_provider,
            )
        instance = MockLLMProvider()

    if provider_name is None:
        _provider_instance = instance

    return instance


def reset_llm_provider() -> None:
    """Reset the cached provider instance."""
    global _provider_instance
    _provider_instance = None
