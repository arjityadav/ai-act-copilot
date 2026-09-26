"""Integration tests against real services.   make up && make migrate && make integration

These are skipped by default (pytest addopts: -m 'not integration'). CI runs the Postgres/Redis
ones against service containers; the Ollama one needs the model pulled (make models).
"""

import os
import uuid

import pytest

from app.retrieval.embed import HashEmbedder
from tests.helpers import make_chunk

pytestmark = pytest.mark.integration
DB = os.environ.get("DATABASE_URL", "postgresql://copilot:copilot@localhost:5432/copilot")


def test_postgres_store_roundtrip():
    from app.db import migrate
    from app.retrieval.store import PostgresStore
    migrate(DB)
    store = PostgresStore(DB)
    tag = uuid.uuid4().hex[:6]
    chunks = [make_chunk(f"art-t{tag}", "social scoring is prohibited", idx=0),
              make_chunk(f"art-u{tag}", "chatbots must disclose they are AI", idx=0)]
    # embeddings must match the vector(768) column
    emb = HashEmbedder(768)
    assert store.upsert(chunks, emb.embed([c.text for c in chunks])) == 2
    assert store.upsert(chunks, emb.embed([c.text for c in chunks])) == 0, "unchanged content is skipped"
    hits = store.keyword_search("social scoring", 5)
    assert any(c.id == chunks[0].id for c, _ in hits)
    vhits = store.vector_search(emb.embed(["chatbots disclose AI"])[0], 3)
    assert vhits and vhits[0][0].id == chunks[1].id
    store.delete_missing([cid for cid in store.all_ids() if tag not in cid])


def test_postgres_assessment_repo():
    from app.jobs.repo import PostgresRepo
    repo = PostgresRepo(DB)
    aid = repo.create({"description": "test"})
    repo.add_event(aid, "intake", "hello")
    repo.update(aid, status="done", result={"ok": True})
    item = repo.get(aid)
    assert item["status"] == "done" and item["result"] == {"ok": True}
    assert repo.events_after(aid)[0]["stage"] == "intake"


def test_redis_ping():
    import redis
    assert redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0")).ping()


def test_ollama_generation_and_embeddings():
    from app.config import get_settings
    from app.llm.provider import OllamaProvider
    from app.retrieval.embed import OllamaEmbedder
    s = get_settings()
    r = OllamaProvider(s).complete([{"role": "user", "content": "Reply with the word OK."}])
    assert r.text and r.output_tokens > 0
    v = OllamaEmbedder(s).embed(["hello"])
    assert v.shape == (1, s.embed_dim)
