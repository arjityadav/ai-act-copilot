"""Train -> log to MLflow -> register -> promote if better (Phase 6).   make train

Also saves data/models/annex3.joblib as a local fallback for serving without MLflow.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib  # noqa: E402

from app.mlops.train import build_pipeline, load_dataset, train_and_log  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--C", type=float, default=4.0)
    args = ap.parse_args()
    info = train_and_log(C=args.C)
    m = info["metrics"]
    print(f"macro F1 {m['macro_f1']:.3f} · accuracy {m['accuracy']:.3f}")
    for label, f1 in sorted(m["per_class_f1"].items(), key=lambda x: x[1]):
        print(f"  {label:<24}{f1:.3f}")
    texts, labels = load_dataset()
    os.makedirs("data/models", exist_ok=True)
    joblib.dump(build_pipeline(args.C).fit(texts, labels), "data/models/annex3.joblib")
    print("Saved local fallback model to data/models/annex3.joblib")
    if info["version"]:
        from app.mlops.registry import promote

        ok, reason = promote(info["version"], m)
        print(f"Version {info['version']}: {'PROMOTED to champion' if ok else 'not promoted'} ({reason})")


if __name__ == "__main__":
    main()
