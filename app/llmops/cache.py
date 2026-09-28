"""PHASE 7 · Semantic cache for /chat.

Read first: notes Day 87 (performance & cost at scale: caching risks).

Many users ask the same things ("Is my chatbot high-risk?"). If a new question's embedding is
very close to a cached one, return the cached answer: zero LLM cost, ~10 ms. The risk: two
questions can look similar but mean different things, so the threshold must be strict and
answers must expire. Measure the hit rate and review hits.
"""

from __future__ import annotations

import time

import numpy as np  # noqa: F401  (for your implementation)


class SemanticCache:
    def __init__(
        self,
        embedder,
        threshold: float = 0.95,
        ttl_s: float = 24 * 3600,
        max_items: int = 1000,
        clock=time.time,
    ):
        self.embedder, self.threshold, self.ttl_s, self.max_items, self.clock = (
            embedder,
            threshold,
            ttl_s,
            max_items,
            clock,
        )
        self.entries: list[dict] = []  # {"vec": np.ndarray, "value": dict, "question": str, "at": float}
        self.hits = 0
        self.misses = 0

    def get(self, question: str) -> dict | None:
        """Return the cached value of the most similar non-expired entry if its cosine similarity
        >= threshold, else None. Update self.hits / self.misses. Drop expired entries while you're at it.
        (Embeddings are normalised, so cosine similarity = dot product.)"""
        q_vec = self.embedder.embed([question], kind="query")[0]
        now = self.clock()
        # Drop expired entries
        self.entries = [e for e in self.entries if now - e["at"] <= self.ttl_s]
        # Find the most similar entry
        best_entry = None
        best_similarity = -1.0
        for entry in self.entries:
            similarity = np.dot(q_vec, entry["vec"])
            if similarity > best_similarity:
                best_similarity = similarity
                best_entry = entry
        if best_entry and best_similarity >= self.threshold:
            self.hits += 1
            return best_entry["value"]
        else:
            self.misses += 1
            return None

    def put(self, question: str, value: dict) -> None:
        """Store the question's embedding with the value and the current time.
        If there are more than max_items entries afterwards, drop the oldest."""
        q_vec = self.embedder.embed([question], kind="query")[0]
        now = self.clock()
        self.entries.append({"vec": q_vec, "value": value, "question": question, "at": now})
        if len(self.entries) > self.max_items:
            # Drop the oldest entry
            self.entries.sort(key=lambda e: e["at"])
            self.entries = self.entries[-self.max_items :]

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
