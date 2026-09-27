"""PHASE 6 · Model registry: promote a new version only if it's good enough and better.

A promotion gate is the MLOps equivalent of a code review: no model reaches production
because someone happened to run a script. The "champion" alias points at the production version.
"""

from __future__ import annotations


def should_promote(
    candidate: dict,
    champion: dict | None,
    min_macro_f1: float = 0.70,
    min_improvement: float = 0.01,
    max_class_drop: float = 0.10,
) -> tuple[bool, str]:
    """Decide whether the candidate replaces the champion. Metrics dicts look like evaluate()'s output.

    Rules, checked in this order (return the first failing reason):
    1. candidate macro_f1 < min_macro_f1                -> (False, "below minimum macro F1")
    2. no champion                                      -> (True, "first model")
    3. candidate macro_f1 < champion macro_f1 + min_improvement -> (False, "not better than champion")
    4. any label present in both per_class_f1 dicts drops by more than max_class_drop
                                                        -> (False, f"regression on class {label}")
    5. otherwise                                        -> (True, "better than champion")
    """
    if candidate["macro_f1"] < min_macro_f1:
        return False, "below minimum macro F1"
    if champion is None:
        return True, "first model"
    if candidate["macro_f1"] < champion["macro_f1"] + min_improvement:
        return False, "not better than champion"
    for label, champ_f1 in champion["per_class_f1"].items():
        if label in candidate["per_class_f1"]:
            cand_f1 = candidate["per_class_f1"][label]
            if champ_f1 > 0 and (champ_f1 - cand_f1) / champ_f1 > max_class_drop:
                return False, f"regression on class {label}"
    return True, "better than champion"


def promote(version: str, candidate_metrics: dict, name: str = "annex3-classifier") -> tuple[bool, str]:
    """(given) Compare with the current champion in MLflow and move the alias if the gate passes."""
    from mlflow import MlflowClient

    client = MlflowClient()
    champion = None
    try:
        mv = client.get_model_version_by_alias(name, "champion")
        champion_run = client.get_run(mv.run_id)
        m = champion_run.data.metrics
        champion = {
            "macro_f1": m["macro_f1"],
            "per_class_f1": {k[3:]: v for k, v in m.items() if k.startswith("f1_")},
        }
    except Exception:
        champion = None
    ok, reason = should_promote(candidate_metrics, champion)
    if ok:
        client.set_registered_model_alias(name, "champion", str(version))
    return ok, reason
