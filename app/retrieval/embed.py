"""Embeddings (given). OllamaEmbedder for real use; HashEmbedder for fast, deterministic tests."""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from app.config import Settings, get_settings


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str], kind: str = "document") -> np.ndarray: ...


class OllamaEmbedder:
    """nomic-embed-text expects task prefixes: 'search_document: ' and 'search_query: '."""

    def __init__(self, settings: Settings | None = None):
        import ollama
        s = settings or get_settings()
        self.model, self.dim = s.embed_model, s.embed_dim
        self._client = ollama.Client(host=s.ollama_host, timeout=s.llm_timeout_s)

    def embed(self, texts, kind="document"):
        prefix = "search_query: " if kind == "query" else "search_document: "
        out = []
        for i in range(0, len(texts), 32):
            r = self._client.embed(model=self.model, input=[prefix + t for t in texts[i:i + 32]])
            out.extend(r["embeddings"])
        v = np.asarray(out, dtype=np.float32)
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)


class HashEmbedder:
    """Bag-of-words hashed into a fixed-size vector. Not semantic, but deterministic: texts sharing
    words get similar vectors, which is enough to test retrieval plumbing without a model."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, texts, kind="document"):
        v = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z0-9]{3,}", t.lower()):
                v[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
