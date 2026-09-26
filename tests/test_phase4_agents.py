"""Phase 4 · Agents: rules, intake, classifier.   make test-phase P=4"""

import json

from app.agents import classifier, intake, rules
from app.agents.schemas import SystemProfile
from tests.helpers import FakeProvider, assessment_json, profile_json, small_corpus


def P(**kw):
    return SystemProfile.model_validate_json(profile_json(**kw))


def test_screen_flags():
    assert rules.screen(P()) == ["annex_iii:employment", "decisions_about_people"]
    flags = rules.screen(P(emotion_recognition=True, uses_biometrics=True, sector="Workplace call centre",
                           interacts_with_people=True, generates_content=True, annex_iii_area="none",
                           decisions_about_people=False, role="unknown"))
    assert flags == ["biometrics", "prohibited:emotion_recognition_work_education", "role_unknown",
                     "transparency:interaction", "transparency:synthetic_content"], flags
    assert "gpai:model" in rules.screen(P(is_general_purpose_model=True))
    assert "annex_i:safety_component" in rules.screen(P(safety_component_of_product=True))
    assert not any(f.startswith("annex_iii") for f in rules.screen(P(annex_iii_area="unknown")))


def test_extract_profile_basic():
    fake = FakeProvider([profile_json()])
    p = intake.extract_profile("We build a CV ranking tool.", fake)
    assert p.annex_iii_area == "employment" and p.role == "provider"
    content = fake.calls[0]["messages"][0]["content"]
    assert content.startswith("<description>\nWe build a CV ranking tool.\n</description>")
    assert "system profile" in fake.calls[0]["system"].lower()


def test_extract_profile_with_answers_and_unknown_role():
    q = "Who uses the outputs?"
    fake = FakeProvider([profile_json(role="unknown", missing_info=[q, "What data is used?"])])
    p = intake.extract_profile("A tool.", fake, answers={q: "Recruiters"})
    content = fake.calls[0]["messages"][0]["content"]
    assert "<clarifications>" in content and "Q: Who uses the outputs?\nA: Recruiters" in content
    assert q not in p.missing_info and "What data is used?" in p.missing_info
    assert any("provider" in m and "deployer" in m for m in p.missing_info), "ask about the role when unknown"


def test_plan_queries():
    qs = classifier.plan_queries(P(), ["annex_iii:employment", "transparency:interaction"])
    assert qs[0].startswith("Article 5") and qs[1].startswith("Article 6")
    assert qs[2] == classifier.AREA_QUERIES["employment"]
    assert qs[3].startswith("Article 50") and qs[-1] == P().purpose
    assert not any("Article 53" in q for q in qs)
    assert any("Article 53" in q for q in classifier.plan_queries(P(annex_iii_area="none"), ["gpai:model"]))


def test_gather_context_dedupes():
    store, emb = small_corpus()
    chunks = classifier.gather_context(["social scoring prohibited", "social scoring prohibited", "Annex III recruitment"],
                                       store, emb, per_query=3, max_chunks=4)
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids)) and len(ids) <= 4


def test_classify_verifies_citations_and_flags():
    store, emb = small_corpus()
    fake = FakeProvider([assessment_json(citations=["art-6", "annex-iii", "art-999"])])
    a = classifier.classify(P(), ["annex_iii:employment", "decisions_about_people"], store, emb, fake)
    assert a.category == "high_risk"
    assert "art-999" not in a.citations and "dropped_unsupported_citations" in a.flags
    assert "annex_iii:employment" in a.flags
    content = fake.calls[0]["messages"][0]["content"]
    assert "<profile>" in content and "<screening_flags>" in content and '<document id="' in content


def test_classify_detects_rule_disagreement():
    store, emb = small_corpus()
    fake = FakeProvider([assessment_json(category="minimal_risk", confidence="high", citations=[])])
    a = classifier.classify(P(), ["annex_iii:employment"], store, emb, fake)
    assert a.confidence == "low" and "rules_disagree_with_llm" in a.flags


def test_classify_lowers_confidence_when_info_missing_and_copies_role():
    store, emb = small_corpus()
    fake = FakeProvider([assessment_json(confidence="high", role="unknown")])
    a = classifier.classify(P(missing_info=["Is it used for hiring decisions?"], role="deployer"),
                            ["annex_iii:employment"], store, emb, fake)
    assert a.confidence == "medium" and a.role == "deployer"


def test_classify_prompt_contains_profile_json():
    store, emb = small_corpus()
    fake = FakeProvider([assessment_json()])
    classifier.classify(P(), [], store, emb, fake)
    content = fake.calls[0]["messages"][0]["content"]
    start = content.index("<profile>") + len("<profile>")
    assert json.loads(content[start:content.index("</profile>")])["name"] == "CV Ranker"
