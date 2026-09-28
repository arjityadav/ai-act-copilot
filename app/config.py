"""Settings, read from environment variables (see .env.example). Twelve-factor style: no secrets in code."""

import os
from dataclasses import dataclass, field


def _env(name, default=None):
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    env: str = field(default_factory=lambda: _env("APP_ENV", "dev"))  # dev | test | prod
    # LLM: "ollama" locally, "anthropic" or "openai" in production. Comma-separated = fallback chain.
    llm_providers: str = field(default_factory=lambda: _env("LLM_PROVIDERS", "ollama"))
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "llama3.1:8b"))
    anthropic_model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4.1-mini"))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("LLM_TIMEOUT_S", "120")))
    # Embeddings (Ollama works on CPU too; nomic-embed-text has 768 dimensions, matching migrations/001).
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "nomic-embed-text"))
    embed_dim: int = field(default_factory=lambda: int(_env("EMBED_DIM", "768")))
    # Storage
    database_url: str = field(
        default_factory=lambda: _env("DATABASE_URL", "postgresql://copilot:copilot@localhost:5432/copilot")
    )
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))
    store: str = field(default_factory=lambda: _env("STORE", "postgres"))  # postgres | memory
    job_mode: str = field(default_factory=lambda: _env("JOB_MODE", "queue"))  # queue (Redis/RQ) | inline
    # Security & limits
    api_key: str | None = field(default_factory=lambda: _env("API_KEY"))  # required in prod
    max_input_chars: int = field(default_factory=lambda: int(_env("MAX_INPUT_CHARS", "8000")))
    # Observability
    langfuse_enabled: bool = field(
        default_factory=lambda: _env("LANGFUSE_ENABLED", "false").lower() == "true"
    )
    mlflow_tracking_uri: str = field(
        default_factory=lambda: _env("MLFLOW_TRACKING_URI", "http://localhost:5000")
    )
    classifier_model_uri: str = field(
        default_factory=lambda: _env("CLASSIFIER_MODEL_URI", "models:/annex3-classifier@champion")
    )


def get_settings() -> Settings:
    return Settings()
