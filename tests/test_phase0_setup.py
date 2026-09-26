"""Phase 0 · The provided infrastructure works (these pass from the start).   make test-phase P=0"""

import glob

import yaml
from pydantic import BaseModel

from app.agents.obligations import load_table
from app.llm.provider import FakeProvider
from app.llm.structured import StructuredOutputError, complete_structured
from app.llmops.prompts import get_prompt
from tests.helpers import small_corpus


class Point(BaseModel):
    x: int
    y: int


def test_structured_output_retries_then_validates():
    fake = FakeProvider(["not json", '```json\n{"x": 1, "y": 2}\n```'])
    assert complete_structured(fake, [{"role": "user", "content": "point"}], Point) == Point(x=1, y=2)
    assert "Your JSON was invalid" in fake.calls[1]["messages"][-1]["content"]


def test_structured_output_gives_up():
    try:
        complete_structured(FakeProvider(["no"] * 3), [{"role": "user", "content": "p"}], Point)
        raise AssertionError("should raise")
    except StructuredOutputError:
        pass


def test_in_memory_store_searches():
    store, emb = small_corpus()
    assert store.count() == 6
    kw = store.keyword_search("credit score insurance", 2)
    assert kw[0][0].provision_id == "annex-iii"
    vec = store.vector_search(emb.embed(["chatbot disclose synthetic content"], kind="query")[0], 2)
    assert vec[0][0].provision_id == "art-50"


def test_prompts_and_data_load():
    for name in ["rag_answer", "intake", "classifier", "writer"]:
        p = get_prompt(name)
        assert p.name == name and p.version and len(p.system) > 100
    table = load_table()
    assert {"ai_literacy", "risk_management", "transparency_disclosure"} <= {t["id"] for t in table}


def test_config_files_are_valid_yaml():
    for path in glob.glob(".github/workflows/*.yml") + ["docker-compose.yml", "monitoring/prometheus.yml"]:
        assert yaml.safe_load(open(path, encoding="utf-8")), path
