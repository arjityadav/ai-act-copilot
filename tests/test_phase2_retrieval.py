"""Phase 2 · Retrieval.   make test-phase P=2"""

from app.retrieval.search import hybrid_search, mrr, recall_at_k, rrf
from tests.helpers import small_corpus


def test_rrf_rewards_agreement():
    fused = rrf([["a", "b", "c"], ["b", "c", "d"]])
    assert fused[0] == "b", "b is ranked high in both lists"
    assert set(fused) == {"a", "b", "c", "d"}


def test_rrf_scores_and_ties():
    assert rrf([["x", "y"]]) == ["x", "y"]
    assert rrf([["a"], ["b"]]) == ["a", "b"], "equal scores keep first-seen order"
    assert rrf([]) == []


def test_recall_and_mrr():
    assert recall_at_k(["a", "b", "c"], ["c", "z"], 3) == 0.5
    assert recall_at_k(["a", "b", "c"], ["c"], 2) == 0.0
    assert recall_at_k(["a"], [], 5) == 1.0
    assert mrr(["x", "y", "z"], ["z"]) == 1 / 3
    assert mrr(["x"], ["q"]) == 0.0


class SpyStore:
    def __init__(self, inner):
        self.inner, self.calls = inner, []

    def vector_search(self, v, k=10):
        self.calls.append(("vector", k))
        return self.inner.vector_search(v, k)

    def keyword_search(self, q, k=10):
        self.calls.append(("keyword", k))
        return self.inner.keyword_search(q, k)


def test_hybrid_search_uses_both_and_finds_the_right_provision():
    store, emb = small_corpus()
    spy = SpyStore(store)
    hits = hybrid_search("Is social scoring prohibited?", spy, emb, k=3, candidates=20)
    assert ("vector", 20) in spy.calls and ("keyword", 20) in spy.calls, "run both searches with k=candidates"
    assert len(hits) <= 3 and hits[0].provision_id == "art-5", [h.id for h in hits]


def test_hybrid_search_exact_terms():
    store, emb = small_corpus()
    ids = [c.provision_id for c in hybrid_search("fines EUR 35 000 000 turnover", store, emb, k=2)]
    assert ids[0] == "art-99", ids


def test_hybrid_search_applies_reranker():
    store, emb = small_corpus()

    class ReverseReranker:
        def rerank(self, query, chunks, top_k):
            self.seen = [c.id for c in chunks]
            return list(reversed(chunks))[:top_k]

    rr = ReverseReranker()
    fused = [c.id for c in hybrid_search("credit score insurance", store, emb, k=30, candidates=30)]
    reranked = [
        c.id for c in hybrid_search("credit score insurance", store, emb, k=2, candidates=30, reranker=rr)
    ]
    assert rr.seen == fused, "the reranker gets the fused candidates, in fused order"
    assert reranked == list(reversed(fused))[:2], "return the reranker's top k"
