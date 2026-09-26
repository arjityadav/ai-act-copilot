"""The ingestion pipeline (given): text -> provisions -> chunks -> embeddings -> store.

Idempotent: re-running with the same text changes nothing; changed articles are re-embedded
(the store compares content hashes); provisions that disappeared are deleted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.ingest.chunk import chunk_provision
from app.ingest.parse import parse_act


@dataclass
class IngestStats:
    provisions: int
    chunks: int
    changed: int
    seconds: float


def ingest_text(text, store, embedder, max_chars=1800, batch=64) -> IngestStats:
    t = time.perf_counter()
    provisions = parse_act(text)
    if not provisions:
        raise ValueError("No articles found. Check the input text (see app/ingest/fetch.py).")
    chunks = [c for p in provisions for c in chunk_provision(p, max_chars=max_chars)]
    changed = 0
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        changed += store.upsert(part, embedder.embed([c.text for c in part], kind="document"))
    store.delete_missing([c.id for c in chunks])
    return IngestStats(len(provisions), len(chunks), changed, time.perf_counter() - t)
