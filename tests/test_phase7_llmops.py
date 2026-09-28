"""Phase 7 · LLMOps: fallback, semantic cache, eval scoring.   make test-phase P=7"""

import pytest

from app.llm.provider import FakeProvider
from app.llmops.cache import SemanticCache
from app.llmops.evals import judge_agreement, score_assessment, summarise
from app.llmops.fallback import AllProvidersFailed, FallbackProvider
from app.retrieval.embed import HashEmbedder


class Broken:
    name, model = "broken", "x"

    def complete(self, messages, **kw):
        raise ConnectionError("down")

    def stream(self, messages, **kw):
        raise ConnectionError("down")
        yield  # pragma: no cover


class DiesMidStream:
    name, model = "flaky", "y"

    def stream(self, messages, **kw):
        yield "partial "
        raise ConnectionError("lost connection")


def test_fallback_complete():
    fb = FallbackProvider([Broken(), FakeProvider(["ok"])])
    assert fb.complete([{"role": "user", "content": "hi"}]).text == "ok"
    assert fb.last_served_by == "fake" and fb.failures == {"broken": 1}
    with pytest.raises(AllProvidersFailed):
        FallbackProvider([Broken(), Broken()]).complete([{"role": "user", "content": "hi"}])


def test_fallback_stream():
    fb = FallbackProvider([Broken(), FakeProvider(["hello world"])])
    assert "".join(fb.stream([{"role": "user", "content": "hi"}])).strip() == "hello world"
    assert fb.last_served_by == "fake"
    fb2 = FallbackProvider([DiesMidStream(), FakeProvider(["never used"])])
    with pytest.raises(ConnectionError):
        list(fb2.stream([{"role": "user", "content": "hi"}]))


def test_semantic_cache():
    now = [1000.0]
    cache = SemanticCache(HashEmbedder(512), threshold=0.9, ttl_s=60, max_items=2, clock=lambda: now[0])
    assert cache.get("Is social scoring prohibited under the AI Act?") is None
    cache.put("Is social scoring prohibited under the AI Act?", {"answer": "Yes [1]."})
    assert cache.get("is social scoring prohibited under the AI act") == {"answer": "Yes [1]."}
    assert cache.get("What are the fines for providers?") is None
    assert cache.hits == 1 and cache.misses == 2 and abs(cache.hit_rate - 1 / 3) < 1e-9
    now[0] += 61
    assert cache.get("Is social scoring prohibited under the AI Act?") is None, "expired"
    for q in ["one question about chatbots", "two question about credit", "three question about fines"]:
        cache.put(q, {"q": q})
    assert len(cache.entries) == 2 and cache.get("one question about chatbots") is None, "oldest evicted"


def test_score_assessment():
    exp = {"category": "high_risk", "annex_iii_area": "employment", "must_cite": ["art-6", "annex-iii"]}
    good = {
        "category": "high_risk",
        "annex_iii_area": "employment",
        "citations": ["art-6", "annex-iii", "art-5"],
        "transparency_obligations": False,
    }
    s = score_assessment(exp, good)
    assert s["passed"] and s["category_correct"] and s["area_correct"] and s["citation_recall"] == 1.0
    assert s["transparency_correct"] is None
    wrong_area = score_assessment(exp, {**good, "annex_iii_area": "education"})
    assert not wrong_area["passed"] and wrong_area["area_correct"] is False
    t = score_assessment(
        {"category": "limited_risk", "transparency": True, "must_cite": ["art-50"]},
        {
            "category": "limited_risk",
            "citations": [],
            "transparency_obligations": True,
            "annex_iii_area": "none",
        },
    )
    assert t["transparency_correct"] and t["citation_recall"] == 0.0 and not t["passed"]


def test_summarise_and_judge_agreement():
    scores = [
        {
            "passed": True,
            "category_correct": True,
            "area_correct": None,
            "transparency_correct": True,
            "citation_recall": 1.0,
        },
        {
            "passed": False,
            "category_correct": False,
            "area_correct": None,
            "transparency_correct": None,
            "citation_recall": 0.5,
        },
    ]
    s = summarise(scores)
    assert s == {
        "n": 2,
        "pass_rate": 0.5,
        "category_accuracy": 0.5,
        "area_accuracy": None,
        "transparency_accuracy": 1.0,
        "mean_citation_recall": 0.75,
    }
    j = judge_agreement([True, True, False, False], [True, False, False, True])
    assert j == {"accuracy": 0.5, "tpr": 0.5, "tnr": 0.5}
    assert judge_agreement([True], [True])["tnr"] is None
