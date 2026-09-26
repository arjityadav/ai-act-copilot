"""PHASE 8 · Prometheus metrics.

Read first: notes Days 85 (observability), 90 (quality dashboard). Prometheus scrapes GET /metrics
every 15 s (monitoring/prometheus.yml); Grafana charts it (monitoring/grafana/).

The four golden signals for an API: traffic, errors, latency, saturation. For an LLM product,
add tokens and cost per provider. The metric objects are given; you record into them.
"""

from __future__ import annotations

import time  # noqa: F401  (for your implementation)

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"], registry=REGISTRY)
HTTP_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["route"],
                         buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60), registry=REGISTRY)
LLM_TOKENS = Counter("llm_tokens_total", "LLM tokens", ["provider", "model", "kind"], registry=REGISTRY)
LLM_COST = Counter("llm_cost_usd_total", "LLM cost in USD", ["provider", "model"], registry=REGISTRY)
LLM_LATENCY = Histogram("llm_call_duration_seconds", "LLM call latency", ["provider"],
                        buckets=(0.25, 0.5, 1, 2, 5, 10, 20, 60, 120), registry=REGISTRY)


def route_label(request) -> str:
    """(given) Use the route template ("/assessments/{aid}"), not the raw path, so ids don't create
    a new time series per request (high cardinality kills Prometheus)."""
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


async def metrics_middleware(request, call_next):
    """Time the request and record it:
    - start = time.perf_counter(); response = await call_next(request)
    - HTTP_REQUESTS.labels(method, route_label(request), str(status)).inc()
    - HTTP_LATENCY.labels(route).observe(seconds)
    - if call_next raises, record status "500" (and the latency) before re-raising
    - return the response
    Don't record requests to /metrics itself.
    """
    # YOUR CODE (replace the line below; until then requests pass through unrecorded)
    return await call_next(request)


def record_llm_call(result) -> None:
    """Record an LLMResult: input/output tokens (kind="input"/"output"), cost, latency."""
    # YOUR CODE (until then, nothing is recorded)
    return None


def metrics_response():
    """(given) Body and content type for GET /metrics."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST

