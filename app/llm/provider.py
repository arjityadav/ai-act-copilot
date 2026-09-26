"""LLM providers behind one interface (given).

Why an interface: develop for free with Ollama, deploy with a cloud API, switch or fall
back without touching agent code, and test everything with FakeProvider.

    provider = get_provider()                                   # from settings
    result = provider.complete([{"role": "user", "content": "Hi"}], system="Be brief.")
    result.text, result.input_tokens, result.output_tokens, result.latency_s
    for piece in provider.stream(messages): ...

Structured output is handled in app/llm/structured.py on top of complete(), the same way
for every provider (JSON schema in the request + Pydantic validation + retries).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import Settings, get_settings

Message = dict[str, str]

# Approximate USD prices per million tokens (input, output). Update from provider pricing pages.
PRICES = {"ollama": (0.0, 0.0), "anthropic": (3.0, 15.0), "openai": (0.4, 1.6), "fake": (0.0, 0.0)}


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    provider: str = ""
    model: str = ""

    @property
    def cost_usd(self) -> float:
        p_in, p_out = PRICES.get(self.provider, (0.0, 0.0))
        return (self.input_tokens * p_in + self.output_tokens * p_out) / 1_000_000


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, messages: list[Message], *, system: str | None = None, json_schema: dict | None = None,
                 temperature: float = 0.0, max_tokens: int = 1500) -> LLMResult: ...

    def stream(self, messages: list[Message], *, system: str | None = None, temperature: float = 0.2,
               max_tokens: int = 1500) -> Iterator[str]: ...


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings):
        import ollama
        self.model = settings.ollama_model
        self._client = ollama.Client(host=settings.ollama_host, timeout=settings.llm_timeout_s)

    def _msgs(self, messages, system):
        return ([{"role": "system", "content": system}] if system else []) + list(messages)

    def complete(self, messages, *, system=None, json_schema=None, temperature=0.0, max_tokens=1500):
        t = time.perf_counter()
        r = self._client.chat(model=self.model, messages=self._msgs(messages, system), format=json_schema,
                              options={"temperature": temperature, "num_predict": max_tokens})
        return LLMResult(r["message"]["content"], r.get("prompt_eval_count") or 0, r.get("eval_count") or 0,
                         time.perf_counter() - t, self.name, self.model)

    def stream(self, messages, *, system=None, temperature=0.2, max_tokens=1500):
        for chunk in self._client.chat(model=self.model, messages=self._msgs(messages, system), stream=True,
                                       options={"temperature": temperature, "num_predict": max_tokens}):
            if chunk["message"]["content"]:
                yield chunk["message"]["content"]


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings):
        import anthropic                                  # pip install ".[cloud]"; reads ANTHROPIC_API_KEY
        self.model = settings.anthropic_model
        self._client = anthropic.Anthropic(timeout=settings.llm_timeout_s, max_retries=2)

    def complete(self, messages, *, system=None, json_schema=None, temperature=0.0, max_tokens=1500):
        t = time.perf_counter()
        kwargs = {"system": system} if system else {}
        r = self._client.messages.create(model=self.model, max_tokens=max_tokens, temperature=temperature,
                                         messages=list(messages), **kwargs)
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return LLMResult(text, r.usage.input_tokens, r.usage.output_tokens, time.perf_counter() - t, self.name, self.model)

    def stream(self, messages, *, system=None, temperature=0.2, max_tokens=1500):
        kwargs = {"system": system} if system else {}
        with self._client.messages.stream(model=self.model, max_tokens=max_tokens, temperature=temperature,
                                          messages=list(messages), **kwargs) as s:
            yield from s.text_stream


class OpenAIProvider:
    name = "openai"

    def __init__(self, settings: Settings):
        import openai                                     # pip install ".[cloud]"; reads OPENAI_API_KEY
        self.model = settings.openai_model
        self._client = openai.OpenAI(timeout=settings.llm_timeout_s, max_retries=2)

    def _msgs(self, messages, system):
        return ([{"role": "system", "content": system}] if system else []) + list(messages)

    def complete(self, messages, *, system=None, json_schema=None, temperature=0.0, max_tokens=1500):
        t = time.perf_counter()
        extra = {"response_format": {"type": "json_object"}} if json_schema else {}
        r = self._client.chat.completions.create(model=self.model, messages=self._msgs(messages, system),
                                                 temperature=temperature, max_tokens=max_tokens, **extra)
        u = r.usage
        return LLMResult(r.choices[0].message.content or "", u.prompt_tokens if u else 0,
                         u.completion_tokens if u else 0, time.perf_counter() - t, self.name, self.model)

    def stream(self, messages, *, system=None, temperature=0.2, max_tokens=1500):
        for ev in self._client.chat.completions.create(model=self.model, messages=self._msgs(messages, system),
                                                       temperature=temperature, max_tokens=max_tokens, stream=True):
            if ev.choices and ev.choices[0].delta.content:
                yield ev.choices[0].delta.content


class FakeProvider:
    """For tests: replies come from a list (used in order) or a function of the messages."""
    name = "fake"
    model = "fake-1"

    def __init__(self, replies: list[str] | Callable[[list[Message], str | None], str]):
        self._replies = replies if callable(replies) else list(replies)
        self.calls: list[dict[str, Any]] = []

    def _next(self, messages, system):
        if callable(self._replies):
            return self._replies(messages, system)
        if not self._replies:
            raise AssertionError("FakeProvider ran out of scripted replies")
        return self._replies.pop(0)

    def complete(self, messages, *, system=None, json_schema=None, temperature=0.0, max_tokens=1500):
        self.calls.append({"messages": list(messages), "system": system, "json_schema": json_schema})
        text = self._next(messages, system)
        return LLMResult(text, sum(len(m["content"]) // 4 for m in messages), len(text) // 4, 0.001, self.name, self.model)

    def stream(self, messages, *, system=None, temperature=0.2, max_tokens=1500):
        self.calls.append({"messages": list(messages), "system": system, "stream": True})
        for word in self._next(messages, system).split(" "):
            yield word + " "


_REGISTRY = {"ollama": OllamaProvider, "anthropic": AnthropicProvider, "openai": OpenAIProvider}


def make_provider(name: str, settings: Settings | None = None) -> LLMProvider:
    return _REGISTRY[name](settings or get_settings())


def get_provider(settings: Settings | None = None) -> LLMProvider:
    """One provider, or a FallbackProvider when LLM_PROVIDERS lists several (Phase 7)."""
    settings = settings or get_settings()
    names = [n.strip() for n in settings.llm_providers.split(",") if n.strip()]
    if len(names) == 1:
        return make_provider(names[0], settings)
    from app.llmops.fallback import FallbackProvider
    return FallbackProvider([make_provider(n, settings) for n in names])
