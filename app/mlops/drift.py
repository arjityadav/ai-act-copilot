"""PHASE 6 · Drift monitoring: are production inputs still like the training data?

Read first: notes Day 85 (observability, drift).

Population Stability Index (PSI) compares two distributions over the same bins:
    PSI = Σ (actual% − expected%) · ln(actual% / expected%)
Rule of thumb: < 0.1 stable, 0.1–0.25 moderate shift, > 0.25 significant shift → investigate / retrain.
"""

from __future__ import annotations

import numpy as np


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10, eps: float = 1e-4) -> float:
    """PSI for a numeric feature (e.g. description length).

    - bin edges from the EXPECTED data's quantiles: np.quantile(expected, np.linspace(0, 1, bins + 1)),
      made unique with np.unique; set the first edge to -inf and the last to +inf
    - counts with np.histogram for both arrays using those edges; convert to proportions
    - replace proportions below eps by eps (avoids log(0) and division by zero)
    - return the PSI as a float
    """
    quantiles = np.quantile(expected, np.linspace(0, 1, bins + 1))
    edges = np.unique(quantiles)
    edges[0] = -np.inf
    edges[-1] = np.inf

    expected_counts, _ = np.histogram(expected, bins=edges)
    actual_counts, _ = np.histogram(actual, bins=edges)

    expected_proportions = expected_counts / len(expected)
    actual_proportions = actual_counts / len(actual)

    expected_proportions = np.maximum(expected_proportions, eps)
    actual_proportions = np.maximum(actual_proportions, eps)

    psi_value = np.sum(
        (actual_proportions - expected_proportions) * np.log(actual_proportions / expected_proportions)
    )
    return float(psi_value)


def categorical_psi(expected_labels: list[str], actual_labels: list[str], eps: float = 1e-4) -> float:
    """PSI over categories (e.g. predicted Annex III areas this week vs the training labels).
    Use the union of categories; proportions per category; floor at eps; same formula."""
    all_labels = set(expected_labels) | set(actual_labels)
    expected_counts = {label: expected_labels.count(label) for label in all_labels}
    actual_counts = {label: actual_labels.count(label) for label in all_labels}

    expected_proportions = np.array([expected_counts[label] / len(expected_labels) for label in all_labels])
    actual_proportions = np.array([actual_counts[label] / len(actual_labels) for label in all_labels])

    expected_proportions = np.maximum(expected_proportions, eps)
    actual_proportions = np.maximum(actual_proportions, eps)

    psi_value = np.sum(
        (actual_proportions - expected_proportions) * np.log(actual_proportions / expected_proportions)
    )
    return float(psi_value)


def drift_report(
    train_texts: list[str], recent_texts: list[str], train_labels: list[str], recent_predictions: list[str]
) -> dict:
    """(given) Summary used by scripts/drift_check.py and the scheduled GitHub Action."""
    lengths = psi(
        np.array([len(t) for t in train_texts], float), np.array([len(t) for t in recent_texts], float)
    )
    labels = categorical_psi(train_labels, recent_predictions)
    worst = max(lengths, labels)
    return {
        "psi_length": round(lengths, 4),
        "psi_labels": round(labels, 4),
        "status": "stable" if worst < 0.1 else "moderate" if worst < 0.25 else "significant",
    }
