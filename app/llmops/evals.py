"""PHASE 7 · Scoring for the evaluation suites (used by evals/run_evals.py and CI).

Read first: notes Days 49 (evals first), 50 (LLM-as-judge), 75 (evaluating agents), 89 (CI for AI).
"""

from __future__ import annotations


def score_assessment(expected: dict, predicted: dict) -> dict:
    """Compare one scenario's expected outcome with the pipeline's assessment (both plain dicts).

    expected:  {"category": "high_risk", "annex_iii_area": "employment", "transparency": false,
                "must_cite": ["art-6", "annex-iii"]}
    predicted: RiskAssessment.model_dump()

    Return:
    - "category_correct":  predicted category == expected category
    - "area_correct":      only when expected has "annex_iii_area": equal areas; otherwise None
    - "transparency_correct": only when expected has "transparency": equal to predicted
                              transparency_obligations; otherwise None
    - "citation_recall":   fraction of must_cite found in predicted citations (1.0 if must_cite empty/missing)
    - "passed":            category_correct and citation_recall >= 0.5 and area/transparency not False
    """
    # YOUR CODE
    raise NotImplementedError


def summarise(scores: list[dict]) -> dict:
    """Aggregate: {"n", "pass_rate", "category_accuracy", "area_accuracy", "transparency_accuracy",
    "mean_citation_recall"}. Accuracies that were never applicable (all None) are None. Round to 3 decimals."""
    # YOUR CODE
    raise NotImplementedError


def judge_agreement(human: list[bool], judge: list[bool]) -> dict:
    """How well an LLM judge matches human labels (True = pass). Return
    {"accuracy", "tpr", "tnr"}: tpr = judge says pass when human says pass; tnr = judge says fail
    when human says fail. Use None for a rate whose denominator is 0."""
    # YOUR CODE
    raise NotImplementedError
