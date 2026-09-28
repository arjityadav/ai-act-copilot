"""Drift check (Phase 6): compare recent assessment inputs with the training data.   make drift

Reads the last N assessment descriptions from Postgres, predicts their Annex III area with the
served classifier, and computes PSI for description length and predicted labels.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.mlops.drift import drift_report  # noqa: E402
from app.mlops.serve import load_classifier  # noqa: E402
from app.mlops.train import load_dataset  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--github-output", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    import psycopg

    with psycopg.connect(s.database_url) as conn:
        rows = conn.execute(
            "SELECT input->>'description' FROM assessments ORDER BY created_at DESC LIMIT %s", (args.limit,)
        ).fetchall()
    recent = [r[0] for r in rows if r[0]]
    if len(recent) < 30:
        print(f"Only {len(recent)} recent inputs; need at least 30 for a meaningful check.")
        return
    clf = load_classifier(s)
    if clf is None:
        sys.exit("No classifier available: run make train first.")
    texts, labels = load_dataset()
    report = drift_report(texts, recent, labels, [clf.predict(t)["label"] for t in recent])
    print(json.dumps(report, indent=2))
    if args.github_output and os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"status={report['status']}\nsummary={json.dumps(report)}\n")


if __name__ == "__main__":
    main()
