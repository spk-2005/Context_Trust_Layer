from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Context Trust Layer"
    app_env: str = "development"

    postgres_server: str = "localhost"
    postgres_user: str = "context_user"
    postgres_password: str = "context_password"
    postgres_db: str = "context_trust"
    postgres_port: int = 5433

    database_url: str | None = None

    # LLM Settings
    llm_provider: str = "mock"  # "mock", "openai", "openrouter", "gemini", "ollama"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: str | None = None

    # OpenRouter / Ox Alpha (Z.ai GLM-5.3-Flash) Settings
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "z-ai/glm-5.3-flash"  # Supports "z-ai/glm-5.3-flash" or "stealth/ox-alpha"
    openrouter_embedding_model: str = "text-embedding-3-small"

    # Ollama Settings (local LLM via Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:1.7b"
    ollama_embedding_model: str = "qwen3:1.7b"
    ollama_timeout: int = 120  # seconds to wait for Ollama completions

    # Trust Engine Defaults
    default_trust_threshold: float = 0.80

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        elif self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", Path(__file__).resolve().parents[2] / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()