"""PHASE 7 · Provider fallback: if the primary model fails, use the next one.

Read first: notes Day 47 (reliability), Day 87 (routing).

LLM_PROVIDERS=anthropic,openai,ollama  -> try Claude, then OpenAI, then the local model.
A provider outage should degrade quality or cost, not take the product down.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class AllProvidersFailed(RuntimeError):
    pass


class FallbackProvider:
    name = "fallback"

    def __init__(self, providers: list):
        if not providers:
            raise ValueError("need at least one provider")
        self.providers = providers
        self.model = providers[0].model
        self.last_served_by: str | None = None      # name of the provider that answered last
        self.failures: dict[str, int] = {}          # provider name -> number of failures

    def complete(self, messages, **kwargs):
        """Try each provider's complete(messages, **kwargs) in order.
        - On success: set last_served_by to that provider's name and return its result.
        - On any exception: count it in failures[provider.name], log a warning, try the next one.
        - If all fail: raise AllProvidersFailed with the names and errors, chained from the last error.
        """
        # YOUR CODE
        raise NotImplementedError

    def stream(self, messages, **kwargs):
        """Like complete(), but only fall back if a provider fails BEFORE yielding its first piece
        (once text reached the user, switching models mid-answer would be confusing): then re-raise.
        Set last_served_by when the first piece arrives."""
        # YOUR CODE
        raise NotImplementedError
