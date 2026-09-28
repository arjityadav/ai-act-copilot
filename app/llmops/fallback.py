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
        self.last_served_by: str | None = None  # name of the provider that answered last
        self.failures: dict[str, int] = {}  # provider name -> number of failures

    def complete(self, messages, **kwargs):
        """Try each provider's complete(messages, **kwargs) in order.
        - On success: set last_served_by to that provider's name and return its result.
        - On any exception: count it in failures[provider.name], log a warning, try the next one.
        - If all fail: raise AllProvidersFailed with the names and errors, chained from the last error.
        """
        last_exc = None
        for provider in self.providers:
            try:
                result = provider.complete(messages, **kwargs)
                self.last_served_by = provider.name
                return result
            except Exception as e:
                self.failures[provider.name] = self.failures.get(provider.name, 0) + 1
                log.warning(f"Provider {provider.name} failed: {e}")
                last_exc = e
        raise AllProvidersFailed(f"All providers failed: {[p.name for p in self.providers]}") from last_exc

    def stream(self, messages, **kwargs):
        errors, last_exc = [], None
        for provider in self.providers:
            try:
                pieces = provider.stream(messages, **kwargs)
                first = next(pieces)  # the provider has to produce something first
            except Exception as e:  # includes StopIteration (an empty answer)
                self.failures[provider.name] = self.failures.get(provider.name, 0) + 1
                log.warning("Provider %s failed before streaming: %s", provider.name, e)
                errors.append(f"{provider.name}: {e!r}")
                last_exc = e
                continue  # nothing has reached the user yet, so try the next one

            # From here on the user has text: no switching models, errors propagate.
            self.last_served_by = provider.name
            yield first
            yield from pieces
            return
        raise AllProvidersFailed("; ".join(errors)) from last_exc
