"""Retrieval metrics on evals/retrieval_eval.jsonl (Phase 2).   make eval-retrieval

Compares vector-only, keyword-only and hybrid search (and hybrid + rerank with --rerank).
Relevance is judged at the provision level: a hit on any chunk of "art-5" counts for "art-5".
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.retrieval.embed import OllamaEmbedder  # noqa: E402
from app.retrieval.search import hybrid_search, mrr, recall_at_k  # noqa: E402
from app.retrieval.store import get_store  # noqa: E402


def provisions(chunks):
    out = []
    for c in chunks:
        if c.provision_id not in out:
            out.append(c.provision_id)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--rerank", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    store, emb = get_store(s), OllamaEmbedder(s)
    reranker = None
    if args.rerank:
        from app.retrieval.search import CrossEncoderReranker

        reranker = CrossEncoderReranker()
    cases = [
        json.loads(line) for line in open("evals/retrieval_eval.jsonl", encoding="utf-8") if line.strip()
    ]
    methods = {
        "vector": lambda q: [c for c, _ in store.vector_search(emb.embed([q], kind="query")[0], 20)],
        "keyword": lambda q: [c for c, _ in store.keyword_search(q, 20)],
        "hybrid": lambda q: hybrid_search(q, store, emb, k=20),
    }
    if reranker:
        methods["hybrid+rerank"] = lambda q: hybrid_search(q, store, emb, k=20, reranker=reranker)
    print(f"{'method':<16}{'recall@' + str(args.k):>10}{'MRR':>8}")
    for name, fn in methods.items():
        r, m = [], []
        for case in cases:
            got = provisions(fn(case["question"]))
            r.append(recall_at_k(got, case["relevant"], args.k))
            m.append(mrr(got, case["relevant"]))
        print(f"{name:<16}{sum(r) / len(r):>10.3f}{sum(m) / len(m):>8.3f}")


if __name__ == "__main__":
    main()
