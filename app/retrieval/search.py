"""PHASE 2 · Hybrid retrieval and retrieval metrics.

Read first: notes Days 51 (vector search), 52 (keyword & hybrid), 57 (measuring retrieval), 58 (reranking).

Legal questions mix exact terms ("Annex III", "Article 50", "CE marking") with meaning
("can I use AI to screen job applicants?"). Keyword search nails the first, embeddings the
second. Reciprocal Rank Fusion combines them using only ranks, so their different score
scales don't matter.
"""

from __future__ import annotations

from typing import Protocol

from app.retrieval.store import Chunk


class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]: ...


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion. `rankings` are lists of ids, best first.
    score(id) = sum over lists containing it of 1 / (k + rank), with rank starting at 1.
    Return all ids sorted by score, highest first. Ties: keep the order in which ids were first seen."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.keys(), key=lambda doc_id: -scores[doc_id])


def hybrid_search(
    query: str, store, embedder, k: int = 8, candidates: int = 30, reranker: Reranker | None = None
) -> list[Chunk]:
    """Return the k best chunks for the query.

    1. vector hits  = store.vector_search(embedder.embed([query], kind="query")[0], candidates)
    2. keyword hits = store.keyword_search(query, candidates)
    3. fuse the two id rankings with rrf(); map ids back to Chunk objects
    4. if a reranker is given: return reranker.rerank(query, fused[:candidates], k)
       otherwise return fused[:k]
    """
    vector_hits = store.vector_search(embedder.embed([query], kind="query")[0], candidates)
    keyword_hits = store.keyword_search(query, candidates)
    fused = rrf([[chunk.id for chunk, _ in vector_hits], [chunk.id for chunk, _ in keyword_hits]])
    by_id = {chunk.id: chunk for chunk, _ in vector_hits + keyword_hits}
    if reranker is not None:
        return reranker.rerank(query, [by_id[doc_id] for doc_id in fused[:candidates]], k)
    return [by_id[doc_id] for doc_id in fused[:k]]


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of `relevant` ids that appear in retrieved[:k]. Empty `relevant` -> 1.0."""
    if len(relevant) == 0:
        return 1.0
    found = set(retrieved[:k]) & set(relevant)
    return len(found) / len(relevant)


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    """1 / rank of the first relevant id in `retrieved` (rank from 1); 0.0 if none is found."""
    relevant_set = set(relevant)
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant_set:
            return 1.0 / rank
    return 0.0


class CrossEncoderReranker:
    """Optional (given): pip install ".[rerank]". Runs on CPU; ~0.2-1 s for 30 chunks."""

    def __init__(self, model="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model)

    def rerank(self, query, chunks, top_k):
        scores = self.model.predict([(query, c.text[:2000]) for c in chunks])
        return [c for _, c in sorted(zip(scores, chunks, strict=False), key=lambda x: -x[0])][:top_k]
