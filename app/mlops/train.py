"""PHASE 6 · Train and evaluate the Annex III area classifier.

Read first: reading pack Days 13–17 (framing, regularisation, metrics, pipelines), notes Days 29 (experiment tracking), 84 (fine-tune vs prompt).

Why a classic model inside an LLM product? It is fast (milliseconds), free, deterministic,
and gives a second opinion: when it disagrees with the LLM classifier, the assessment gets a
flag for human review. It also gives you a real MLOps lifecycle to show: versioned data,
tracked experiments, a registry with a promotion gate, monitoring and retraining.

Data: data/training/annex3.csv with columns text,label (seed file included; grow it with
scripts/generate_training_data.py and review the rows by hand).
"""

from __future__ import annotations

import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "training")


def load_dataset(path: str | None = None):
    """(given) -> (texts, labels) as lists."""
    import csv
    path = path or os.path.join(DATA, "annex3.csv")
    if not os.path.exists(path):
        path = os.path.join(DATA, "annex3_seed.csv")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r["text"] for r in rows], [r["label"] for r in rows]


def split(texts, labels, test_size=0.25, seed=42):
    """(given) Stratified split so every label appears in both sets."""
    return train_test_split(texts, labels, test_size=test_size, random_state=seed, stratify=labels)


def build_pipeline(C: float = 4.0) -> Pipeline:
    """A scikit-learn Pipeline with two steps:
    - "tfidf": TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    - "clf":   LogisticRegression(C=C, max_iter=2000, class_weight="balanced")
    """
    # YOUR CODE
    raise NotImplementedError


def evaluate(model, texts, labels) -> dict:
    """Return {"macro_f1": ..., "accuracy": ..., "per_class_f1": {label: f1, ...}} as plain floats.
    Use f1_score(..., average="macro", zero_division=0) and f1_score(..., average=None, labels=sorted(set(labels)))."""
    # YOUR CODE
    raise NotImplementedError


def train_and_log(C: float = 4.0, data_path: str | None = None, register: bool = True) -> dict:
    """(given) Train, evaluate, log to MLflow (if installed), register a new model version.
    Returns {"metrics": ..., "run_id": ..., "version": ...}."""
    texts, labels = load_dataset(data_path)
    X_tr, X_te, y_tr, y_te = split(texts, labels)
    model = build_pipeline(C).fit(X_tr, y_tr)
    metrics = evaluate(model, X_te, y_te)
    info = {"metrics": metrics, "run_id": None, "version": None}
    try:
        import mlflow
        import mlflow.sklearn
    except ImportError:
        print("MLflow not installed (pip install '.[mlops]'); skipping tracking.")
        return info
    mlflow.set_experiment("annex3-classifier")
    with mlflow.start_run() as run:
        mlflow.log_params({"C": C, "n_train": len(X_tr), "n_test": len(X_te), "labels": len(set(labels)),
                           "data_path": data_path or "default"})
        mlflow.log_metrics({"macro_f1": metrics["macro_f1"], "accuracy": metrics["accuracy"],
                            **{f"f1_{k}": v for k, v in metrics["per_class_f1"].items()}})
        name = "annex3-classifier" if register else None
        logged = mlflow.sklearn.log_model(model, name="model", registered_model_name=name,
                                          input_example=np.array(X_te[:2], dtype=object))
        info["run_id"] = run.info.run_id
        info["version"] = getattr(logged, "registered_model_version", None)
    return info
