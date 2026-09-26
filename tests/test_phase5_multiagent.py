"""Phase 5 · Multi-agent pipeline: obligations, gaps, verifier, LangGraph wiring, assessment API.
make test-phase P=5   (the graph tests need langgraph installed: uv sync)"""

from datetime import date

import pytest

from app.agents import gaps, graph, obligations, verifier
from app.agents.schemas import Obligation, Report, RiskAssessment, VerificationResult
from tests.helpers import FakeProvider, assessment_json, profile_json, small_corpus


def A(**kw):
    return RiskAssessment.model_validate_json(assessment_json(**kw))


def ids(obs):
    return [o.id for o in obs]


def test_lookup_high_risk_provider_vs_deployer():
    prov = ids(obligations.lookup(A(role="provider")))
    assert prov[0] == "ai_literacy" and "risk_management" in prov and "deployer_duties" not in prov
    dep = ids(obligations.lookup(A(role="deployer")))
    assert "deployer_duties" in dep and "fria" in dep and "risk_management" not in dep
    both = ids(obligations.lookup(A(role="unknown")))
    assert "deployer_duties" in both and "risk_management" in both


def test_lookup_other_categories():
    assert ids(obligations.lookup(A(category="prohibited", role="provider"))) == ["ai_literacy", "stop_prohibited"]
    lim = ids(obligations.lookup(A(category="limited_risk", transparency_obligations=True)))
    assert "transparency_disclosure" in lim and "voluntary_codes" in lim
    assert "transparency_disclosure" not in ids(obligations.lookup(A(category="minimal_risk")))
    assert "gpai_documentation" in ids(obligations.lookup(A(category="gpai")))
    assert all(isinstance(o, Obligation) for o in obligations.lookup(A()))


def ob(i, applies_from):
    return Obligation(id=i, title=i.title(), articles=["art-9"], applies_to="provider", applies_from=applies_from, description="")


def test_find_gaps_status_priority_and_order():
    today = date(2026, 10, 1)
    obs = [ob("a", "2027-12-02"), ob("b", "2025-02-02"), ob("c", "2027-06-01"), ob("d", "2027-12-02")]
    g = gaps.find_gaps(obs, {"a": "Yes", "b": "no", "c": "no", "d": "partial"}, today=today)
    by = {x.obligation_id: x for x in g}
    assert by["a"].status == "in_place" and by["a"].priority == "low"
    assert by["b"].status == "missing" and by["b"].priority == "high", "already applies and missing"
    assert by["c"].priority == "high", "applies within a year and missing"
    assert by["d"].status == "partial" and by["d"].priority == "medium"
    assert [x.obligation_id for x in g] == ["b", "c", "d", "a"]
    assert gaps.find_gaps([ob("e", "2025-01-01")], {}, today=today)[0].status == "unknown"


def test_verify_report():
    known = {"art-6", "annex-iii", "art-9"}
    obs = [ob("risk", "2027-12-02")]
    good = Report(markdown="## Summary\nThis is a high-risk system (Article 6, Annex III). Deadline 2027-12-02.\n"
                           "## Disclaimer\nDecision support, not legal advice.", cited_provisions=["art-6", "annex-iii"])
    assert verifier.verify_report(good, A(), obs, known).passed
    bad = Report(markdown="Minimal stuff under Article 77.", cited_provisions=["art-77"])
    issues = verifier.verify_report(bad, A(), obs, known).issues
    assert any("art-77" in i for i in issues)
    assert any("high-risk" in i for i in issues)
    assert any("2027-12-02" in i for i in issues)
    assert "Missing disclaimer" in issues


def test_routing():
    from app.agents.schemas import SystemProfile
    p = SystemProfile.model_validate_json(profile_json(missing_info=["Who uses it?"]))
    assert graph.route_after_intake({"profile": p, "answers": {}}) == "clarify"
    assert graph.route_after_intake({"profile": p, "answers": {"Who uses it?": "HR"}}) == "screen"
    ok, fail = VerificationResult(passed=True), VerificationResult(passed=False, issues=["x"])
    assert graph.route_after_verify({"verification": fail, "attempts": 1}) == "write"
    assert graph.route_after_verify({"verification": fail, "attempts": graph.MAX_WRITE_ATTEMPTS}) == "finish"
    assert graph.route_after_verify({"verification": ok, "attempts": 1}) == "finish"


GOOD_REPORT = ("## Summary\nThis high-risk system (Annex III, Article 6) is built by a provider.\n"
               "## Obligations and deadlines\n- AI literacy: 2025-02-02\n- Everything else: 2027-12-02\n"
               "## Disclaimer\nDecision support, not legal advice.")


def scripted(reports):
    reports = list(reports)

    def reply(messages, system):
        system = system or ""
        if "intake analyst" in system:
            return profile_json()
        if "You classify AI systems" in system:
            return assessment_json()
        if "compliance summary" in system:
            return reports.pop(0)
        raise AssertionError("unexpected prompt")
    return reply


def deps_with(provider, events=None, ml=None):
    store, emb = small_corpus()
    return graph.PipelineDeps(provider=provider, store=store, embedder=emb, events=events, ml_classifier=ml,
                              today=date(2026, 10, 1))


def test_graph_full_run_with_retry():
    pytest.importorskip("langgraph")
    events = []

    class FakeML:
        def predict(self, text):
            return {"label": "education", "probability": 0.7}

    deps = deps_with(FakeProvider(scripted(["Draft without the required parts.", GOOD_REPORT])),
                     events=lambda s, m: events.append(s), ml=FakeML())
    final = graph.run_pipeline({"description": "We build a CV ranking tool.", "answers": {}, "practices": {}}, deps)
    assert final["status"] == "done" and final["verification"].passed and final["attempts"] == 2
    assert "ml_disagrees_with_llm" in final["assessment"].flags
    assert final["obligations"] and final["gaps"]
    for stage in ["intake", "screen", "classify", "ml_prescreen", "obligations", "gaps", "write", "verify"]:
        assert stage in events, f"node {stage} did not run"


def test_graph_asks_for_clarification():
    pytest.importorskip("langgraph")

    def reply(messages, system):
        return profile_json(missing_info=["Do you develop it or buy it?"])

    final = graph.run_pipeline({"description": "An AI tool.", "answers": {}, "practices": {}},
                               deps_with(FakeProvider(reply)))
    assert final["status"] == "needs_input" and final["questions"] == ["Do you develop it or buy it?"]
    assert "assessment" not in final


def test_assessment_api_inline(monkeypatch=None):
    pytest.importorskip("langgraph")
    from fastapi.testclient import TestClient

    from app.api import deps as api_deps
    from app.jobs import queue, repo
    from app.main import create_app

    r = repo.InMemoryRepo()
    original = queue.build_deps
    queue.build_deps = lambda rp, aid, settings=None: deps_with(FakeProvider(scripted([GOOD_REPORT])),
                                                                events=lambda s, m: rp.add_event(aid, s, m))
    try:
        app = create_app()
        app.dependency_overrides[api_deps.assessments_dep] = lambda: r
        client = TestClient(app)
        resp = client.post("/assessments", json={"description": "We build a CV ranking tool for recruiters."})
        assert resp.status_code == 202
        item = client.get(f"/assessments/{resp.json()['id']}").json()
        assert item["status"] == "done", item
        assert item["result"]["assessment"]["category"] == "high_risk"
        assert client.get("/assessments/nope").status_code == 404
    finally:
        queue.build_deps = original
