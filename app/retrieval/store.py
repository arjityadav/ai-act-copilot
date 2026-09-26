"""Chunk storage and the two basic searches (given).

Both stores have the same methods:
    upsert(chunks, embeddings)               insert or update (skips unchanged content)
    vector_search(query_vec, k)  -> [(Chunk, score)]   cosine similarity, highest first
    keyword_search(query, k)     -> [(Chunk, score)]   BM25 / Postgres full-text rank
    get(chunk_id) -> Chunk | None ;  all_ids() -> set[str] ;  count() -> int

InMemoryStore: tests and quick experiments. PostgresStore: pgvector (HNSW) + tsvector (GIN).
Phase 2 combines the two searches into hybrid search (app/retrieval/search.py).
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Chunk:
    id: str                          # e.g. "art-5-p1-0"
    provision_id: str                # e.g. "art-5" or "annex-iii"
    kind: str                        # "article" | "annex"
    number: str                      # "5" or "III"
    title: str                       # "Prohibited AI practices"
    text: str                        # chunk text incl. a context header
    chapter: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        return f"Article {self.number}" if self.kind == "article" else f"Annex {self.number}"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()[:16]


def _tokens(text):
    return re.findall(r"[a-z0-9]{2,}", text.lower())


class InMemoryStore:
    def __init__(self):
        self.chunks: dict[str, Chunk] = {}
        self.vectors: dict[str, np.ndarray] = {}

    def upsert(self, chunks, embeddings):
        changed = 0
        for c, v in zip(chunks, embeddings):
            old = self.chunks.get(c.id)
            if old is None or old.content_hash != c.content_hash:
                changed += 1
            self.chunks[c.id], self.vectors[c.id] = c, np.asarray(v, dtype=np.float32)
        return changed

    def delete_missing(self, keep_ids):
        for cid in set(self.chunks) - set(keep_ids):
            self.chunks.pop(cid)
            self.vectors.pop(cid)

    def get(self, chunk_id):
        return self.chunks.get(chunk_id)

    def all_ids(self):
        return set(self.chunks)

    def count(self):
        return len(self.chunks)

    def vector_search(self, query_vec, k=10):
        if not self.chunks:
            return []
        ids = list(self.chunks)
        M = np.stack([self.vectors[i] for i in ids])
        q = np.asarray(query_vec, dtype=np.float32)
        sims = M @ q / (np.linalg.norm(M, axis=1) * max(np.linalg.norm(q), 1e-12) + 1e-12)
        order = np.argsort(-sims)[:k]
        return [(self.chunks[ids[i]], float(sims[i])) for i in order]

    def keyword_search(self, query, k=10, k1=1.5, b=0.75):
        docs = {cid: _tokens(c.title + " " + c.text) for cid, c in self.chunks.items()}
        if not docs:
            return []
        n, avgdl = len(docs), sum(map(len, docs.values())) / len(docs)
        df = Counter(w for toks in docs.values() for w in set(toks))
        q = set(_tokens(query))
        scores = {}
        for cid, toks in docs.items():
            tf = Counter(toks)
            s = sum(math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * (k1 + 1)
                    / (tf[w] + k1 * (1 - b + b * len(toks) / avgdl)) for w in q if tf[w])
            if s > 0:
                scores[cid] = s
        top = sorted(scores, key=scores.get, reverse=True)[:k]
        return [(self.chunks[c], scores[c]) for c in top]


class PostgresStore:
    """pgvector + full-text search. Needs `docker compose up db` and migrations (make migrate)."""

    def __init__(self, database_url: str):
        import psycopg
        self._psycopg = psycopg
        self.url = database_url

    def _conn(self):
        return self._psycopg.connect(self.url, autocommit=True)

    @staticmethod
    def _vec(v):
        return "[" + ",".join(f"{x:.6f}" for x in np.asarray(v, dtype=np.float32)) + "]"

    @staticmethod
    def _row_to_chunk(r):
        return Chunk(id=r[0], provision_id=r[1], kind=r[2], number=r[3], title=r[4], text=r[5], chapter=r[6] or "")

    _COLS = "id, provision_id, kind, number, title, text, chapter"

    def upsert(self, chunks, embeddings):
        sql = f"""INSERT INTO chunks ({self._COLS}, content_hash, embedding)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                  ON CONFLICT (id) DO UPDATE SET provision_id = EXCLUDED.provision_id, kind = EXCLUDED.kind,
                    number = EXCLUDED.number, title = EXCLUDED.title, text = EXCLUDED.text,
                    chapter = EXCLUDED.chapter, content_hash = EXCLUDED.content_hash,
                    embedding = EXCLUDED.embedding, updated_at = now()
                  WHERE chunks.content_hash <> EXCLUDED.content_hash"""
        changed = 0
        with self._conn() as conn, conn.cursor() as cur:
            for c, v in zip(chunks, embeddings):
                cur.execute(sql, (c.id, c.provision_id, c.kind, c.number, c.title, c.text, c.chapter,
                                  c.content_hash, self._vec(v)))
                changed += cur.rowcount
        return changed

    def delete_missing(self, keep_ids):
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE NOT (id = ANY(%s))", (list(keep_ids),))

    def get(self, chunk_id):
        with self._conn() as conn:
            r = conn.execute(f"SELECT {self._COLS} FROM chunks WHERE id = %s", (chunk_id,)).fetchone()
        return self._row_to_chunk(r) if r else None

    def all_ids(self):
        with self._conn() as conn:
            return {r[0] for r in conn.execute("SELECT id FROM chunks").fetchall()}

    def count(self):
        with self._conn() as conn:
            return conn.execute("SELECT count(*) FROM chunks").fetchone()[0]

    def vector_search(self, query_vec, k=10):
        v = self._vec(query_vec)
        with self._conn() as conn:
            rows = conn.execute(f"""SELECT {self._COLS}, 1 - (embedding <=> %s::vector) AS score
                                    FROM chunks ORDER BY embedding <=> %s::vector LIMIT %s""", (v, v, k)).fetchall()
        return [(self._row_to_chunk(r), float(r[7])) for r in rows]

    def keyword_search(self, query, k=10):
        with self._conn() as conn:
            rows = conn.execute(f"""SELECT {self._COLS}, ts_rank_cd(tsv, q) AS score
                                    FROM chunks, websearch_to_tsquery('english', %s) AS q
                                    WHERE tsv @@ q ORDER BY score DESC LIMIT %s""", (query, k)).fetchall()
        return [(self._row_to_chunk(r), float(r[7])) for r in rows]


def get_store(settings=None):
    from app.config import get_settings
    s = settings or get_settings()
    return InMemoryStore() if s.store == "memory" else PostgresStore(s.database_url)
