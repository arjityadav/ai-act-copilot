"""LLM call tracing (given): wraps a provider so every call is recorded with tokens, latency,
cost, agent and prompt version. Records go to Postgres (llm_calls table), and to Langfuse
when LANGFUSE_ENABLED=true (set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST).

    provider = TracedProvider(get_provider(), agent="classifier", sink=PostgresSink(url))
"""

from __future__ import annotations

import contextvars
import uuid

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def new_trace_id() -> str:
    tid = uuid.uuid4().hex
    trace_id_var.set(tid)
    return tid


class ListSink:
    def __init__(self):
        self.records = []

    def write(self, record: dict):
        self.records.append(record)


class PostgresSink:
    def __init__(self, url):
        self.url = url

    def write(self, r: dict):
        import psycopg

        with psycopg.connect(self.url, autocommit=True) as c:
            c.execute(
                """INSERT INTO llm_calls (trace_id, agent, provider, model, prompt_name, prompt_version,
                         input_tokens, output_tokens, latency_ms, cost_usd) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    r["trace_id"],
                    r["agent"],
                    r["provider"],
                    r["model"],
                    r.get("prompt_name"),
                    r.get("prompt_version"),
                    r["input_tokens"],
                    r["output_tokens"],
                    r["latency_ms"],
                    r["cost_usd"],
                ),
            )


class LangfuseSink:
    """Sends each call to Langfuse as a generation (pip install ".[tracing]"; LANGFUSE_* env vars)."""

    def __init__(self):
        from langfuse import get_client

        self.client = get_client()

    def write(self, r: dict):
        gen = self.client.start_observation(
            name=r["agent"],
            as_type="generation",
            model=r["model"],
            version=r.get("prompt_version"),
            metadata={"trace_id": r["trace_id"], "prompt": r.get("prompt_name")},
            usage_details={"input": r["input_tokens"], "output": r["output_tokens"]},
            cost_details={"total": float(r["cost_usd"])},
        )
        gen.end()


class MultiSink:
    def __init__(self, sinks):
        self.sinks = sinks

    def write(self, record):
        for s in self.sinks:
            try:
                s.write(record)
            except Exception:
                pass


def default_sink(settings):
    sinks = []
    if settings.store == "postgres":
        sinks.append(PostgresSink(settings.database_url))
    if settings.langfuse_enabled:
        try:
            sinks.append(LangfuseSink())
        except Exception:
            pass
    return MultiSink(sinks) if sinks else ListSink()


class TracedProvider:
    def __init__(
        self, inner, agent: str, sink, prompt_name: str | None = None, prompt_version: str | None = None
    ):
        self.inner, self.agent, self.sink = inner, agent, sink
        self.prompt_name, self.prompt_version = prompt_name, prompt_version
        self.name, self.model = inner.name, inner.model

    def complete(self, messages, **kwargs):
        result = self.inner.complete(messages, **kwargs)
        record = {
            "trace_id": trace_id_var.get() or "",
            "agent": self.agent,
            "provider": result.provider,
            "model": result.model,
            "prompt_name": self.prompt_name,
            "prompt_version": self.prompt_version,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "latency_ms": int(result.latency_s * 1000),
            "cost_usd": round(result.cost_usd, 6),
        }
        try:
            self.sink.write(record)
        except Exception:
            pass  # tracing must never break the product
        try:
            from app.observability.metrics import record_llm_call

            record_llm_call(result)
        except Exception:
            pass
        return result

    def stream(self, messages, **kwargs):
        yield from self.inner.stream(messages, **kwargs)
