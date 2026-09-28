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
    category_correct = predicted.get("category") == expected.get("category")
    area_correct = (
        None
        if "annex_iii_area" not in expected
        else predicted.get("annex_iii_area") == expected.get("annex_iii_area")
    )
    transparency_correct = (
        None
        if "transparency" not in expected
        else predicted.get("transparency_obligations") == expected.get("transparency")
    )
    citation_recall = (
        1.0
        if not expected.get("must_cite")
        else len(set(expected.get("must_cite", [])) & set(predicted.get("citations", [])))
        / len(expected.get("must_cite"))
    )
    passed = (
        category_correct
        and (not expected.get("must_cite") or citation_recall >= 0.5)
        and (expected.get("annex_iii_area") is None or area_correct)
        and (expected.get("transparency") is None or transparency_correct)
    )
    return {
        "category_correct": category_correct,
        "area_correct": area_correct,
        "transparency_correct": transparency_correct,
        "citation_recall": citation_recall,
        "passed": passed,
    }


def summarise(scores: list[dict]) -> dict:
    """Aggregate: {"n", "pass_rate", "category_accuracy", "area_accuracy", "transparency_accuracy",
    "mean_citation_recall"}. Accuracies that were never applicable (all None) are None. Round to 3 decimals."""
    n = len(scores)
    if n == 0:
        return {
            "n": 0,
            "pass_rate": None,
            "category_accuracy": None,
            "area_accuracy": None,
            "transparency_accuracy": None,
            "mean_citation_recall": None,
        }
    pass_rate = sum(s["passed"] for s in scores) / n
    category_accuracy = sum(s["category_correct"] for s in scores) / n
    area_scores = [s["area_correct"] for s in scores if s["area_correct"] is not None]
    area_accuracy = (sum(area_scores) / len(area_scores)) if area_scores else None
    transparency_scores = [s["transparency_correct"] for s in scores if s["transparency_correct"] is not None]
    transparency_accuracy = (
        (sum(transparency_scores) / len(transparency_scores)) if transparency_scores else None
    )
    mean_citation_recall = sum(s["citation_recall"] for s in scores) / n
    return {
        "n": n,
        "pass_rate": round(pass_rate, 3),
        "category_accuracy": round(category_accuracy, 3),
        "area_accuracy": round(area_accuracy, 3) if area_accuracy is not None else None,
        "transparency_accuracy": round(transparency_accuracy, 3)
        if transparency_accuracy is not None
        else None,
        "mean_citation_recall": round(mean_citation_recall, 3),
    }


def judge_agreement(human: list[bool], judge: list[bool]) -> dict:
    """How well an LLM judge matches human labels (True = pass). Return
    {"accuracy", "tpr", "tnr"}: tpr = judge says pass when human says pass; tnr = judge says fail
    when human says fail. Use None for a rate whose denominator is 0."""
    assert len(human) == len(judge), "human and judge lists must be the same length"
    n = len(human)
    if n == 0:
        return {"accuracy": None, "tpr": None, "tnr": None}
    correct = sum(h == j for h, j in zip(human, judge, strict=False))
    accuracy = correct / n
    true_positive = sum(h and j for h, j in zip(human, judge, strict=False))
    false_negative = sum(h and not j for h, j in zip(human, judge, strict=False))
    true_negative = sum(not h and not j for h, j in zip(human, judge, strict=False))
    false_positive = sum(not h and j for h, j in zip(human, judge, strict=False))
    tpr = (true_positive / (true_positive + false_negative)) if (true_positive + false_negative) > 0 else None
    tnr = (true_negative / (true_negative + false_positive)) if (true_negative + false_positive) > 0 else None
    return {
        "accuracy": round(accuracy, 3),
        "tpr": round(tpr, 3) if tpr is not None else None,
        "tnr": round(tnr, 3) if tnr is not None else None,
    }
