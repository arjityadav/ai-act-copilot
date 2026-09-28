"""Phase 8 · Observability: Prometheus metrics.   make test-phase P=8"""

from fastapi.testclient import TestClient

from app.llm.provider import LLMResult
from app.main import create_app
from app.observability import metrics


def sample(name, labels):
    return metrics.REGISTRY.get_sample_value(name, labels) or 0.0


def test_http_metrics_use_route_templates():
    client = TestClient(create_app())
    before = sample("http_requests_total", {"method": "GET", "route": "/health", "status": "200"})
    client.get("/health")
    client.get("/health")
    assert sample("http_requests_total", {"method": "GET", "route": "/health", "status": "200"}) == before + 2
    assert sample("http_request_duration_seconds_count", {"route": "/health"}) >= 2
    client.get("/assessments/abc-123")
    text = client.get("/metrics").text
    assert 'route="/assessments/{aid}"' in text, "use the route template, not the raw path"
    assert 'route="/metrics"' not in text, "don't record /metrics itself"


def test_record_llm_call():
    r = LLMResult(
        text="x", input_tokens=100, output_tokens=40, latency_s=1.5, provider="anthropic", model="m"
    )
    before_in = sample("llm_tokens_total", {"provider": "anthropic", "model": "m", "kind": "input"})
    metrics.record_llm_call(r)
    assert (
        sample("llm_tokens_total", {"provider": "anthropic", "model": "m", "kind": "input"})
        == before_in + 100
    )
    assert sample("llm_tokens_total", {"provider": "anthropic", "model": "m", "kind": "output"}) >= 40
    assert sample("llm_cost_usd_total", {"provider": "anthropic", "model": "m"}) > 0
    assert sample("llm_call_duration_seconds_count", {"provider": "anthropic"}) >= 1
