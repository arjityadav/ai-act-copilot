"""Phase 6 · MLOps: training, promotion gate, drift.   make test-phase P=6"""

import numpy as np
from sklearn.pipeline import Pipeline

from app.mlops import drift, registry, train


def test_build_pipeline():
    p = train.build_pipeline(C=2.0)
    assert isinstance(p, Pipeline) and [n for n, _ in p.steps] == ["tfidf", "clf"]
    assert p.named_steps["clf"].C == 2.0 and p.named_steps["tfidf"].ngram_range == (1, 2)


def test_train_and_evaluate_on_seed_data():
    texts, labels = train.load_dataset()
    X_tr, X_te, y_tr, y_te = train.split(texts, labels)
    m = train.evaluate(train.build_pipeline().fit(X_tr, y_tr), X_te, y_te)
    assert set(m) == {"macro_f1", "accuracy", "per_class_f1"}
    assert 0 <= m["macro_f1"] <= 1 and isinstance(m["macro_f1"], float)
    assert set(m["per_class_f1"]) == set(y_te)
    assert m["accuracy"] > 1 / 9, "should beat random guessing even on the small seed set"


def M(f1, per=None):
    return {"macro_f1": f1, "per_class_f1": per or {}}


def test_should_promote_rules():
    assert registry.should_promote(M(0.6), None) == (False, "below minimum macro F1")
    assert registry.should_promote(M(0.8), None) == (True, "first model")
    assert registry.should_promote(M(0.805), M(0.80)) == (False, "not better than champion")
    ok, reason = registry.should_promote(
        M(0.85, {"employment": 0.6, "education": 0.9}), M(0.80, {"employment": 0.8, "education": 0.8})
    )
    assert not ok and reason == "regression on class employment"
    assert registry.should_promote(M(0.85, {"x": 0.8}), M(0.80, {"x": 0.85})) == (
        True,
        "better than champion",
    )


def test_psi():
    rng = np.random.default_rng(0)
    a = rng.normal(100, 20, 5000)
    assert drift.psi(a, rng.normal(100, 20, 5000)) < 0.05, "same distribution: stable"
    assert drift.psi(a, rng.normal(160, 20, 5000)) > 0.25, "shifted distribution: significant"


def test_categorical_psi_and_report():
    train_labels = ["none"] * 50 + ["employment"] * 50
    assert drift.categorical_psi(train_labels, ["none"] * 49 + ["employment"] * 51) < 0.01
    assert drift.categorical_psi(train_labels, ["education"] * 100) > 1
    rng = np.random.default_rng(1)
    train_texts = ["x" * int(n) for n in rng.integers(50, 150, 100)]
    recent_texts = ["x" * int(n) for n in rng.integers(400, 600, 100)]
    rep = drift.drift_report(train_texts, recent_texts, train_labels, train_labels)
    assert rep["status"] == "significant" and rep["psi_labels"] < 0.01
