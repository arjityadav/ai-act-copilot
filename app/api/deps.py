"""Dependency providers (given). Tests replace these with app.dependency_overrides."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Header, HTTPException

from app.config import Settings, get_settings


@lru_cache
def settings_dep() -> Settings:
    return get_settings()


@lru_cache
def store_dep():
    from app.retrieval.store import get_store

    return get_store(settings_dep())


@lru_cache
def embedder_dep():
    from app.retrieval.embed import OllamaEmbedder

    return OllamaEmbedder(settings_dep())


@lru_cache
def provider_dep():
    """The configured provider, wrapped so every call is traced (tokens, latency, cost)."""
    from app.llm.provider import get_provider
    from app.llmops.tracing import TracedProvider, default_sink

    return TracedProvider(get_provider(settings_dep()), agent="copilot", sink=default_sink(settings_dep()))


@lru_cache
def assessments_dep():
    from app.jobs.repo import get_repo

    return get_repo(settings_dep())


@lru_cache
def cache_dep():
    """Semantic cache for /chat (Phase 7). None until you've built it."""
    try:
        from app.llmops.cache import SemanticCache

        return SemanticCache(embedder_dep())
    except Exception:
        return None


def require_api_key(x_api_key: str | None = Header(default=None)):
    """If API_KEY is set (always in prod), every request must send it as the X-API-Key header."""
    expected = settings_dep().api_key
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
