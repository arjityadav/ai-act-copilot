"""Grow the classifier's training data with synthetic examples (Phase 6).

    uv run python scripts/generate_training_data.py --per-label 60

Writes data/training/annex3.csv = seed rows + generated rows. Then REVIEW the new rows by hand
(open the CSV, fix or delete wrong labels): synthetic data is a draft, not ground truth.
Record what you changed in docs/MODEL_CARD.md (data section). Version the file (git or DVC).
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel  # noqa: E402

from app.llm.provider import get_provider  # noqa: E402
from app.llm.structured import complete_structured  # noqa: E402

LABELS = {
    "none": "ordinary business AI with no Annex III use (recommendations, forecasting, spam filters, translation, quality inspection)",
    "biometrics": "remote biometric identification, biometric categorisation, emotion recognition",
    "critical_infrastructure": "safety components in digital infrastructure, road traffic, water, gas, heating, electricity",
    "education": "admission, evaluating learning outcomes, deciding education level, detecting cheating in tests",
    "employment": "recruitment, candidate screening, promotion/termination decisions, task allocation, monitoring workers",
    "essential_services": "public benefits eligibility, creditworthiness, life/health insurance pricing, emergency call triage",
    "law_enforcement": "police risk assessments, evidence reliability, profiling in investigations",
    "migration": "asylum, visa and residence applications, border risk assessment",
    "justice_democracy": "assisting judges or arbitrators, influencing elections or voting behaviour",
}


class Batch(BaseModel):
    descriptions: list[str]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-label", type=int, default=40)
    args = ap.parse_args()
    provider = get_provider()
    rows = list(csv.DictReader(open("data/training/annex3_seed.csv", encoding="utf-8")))
    for label, meaning in LABELS.items():
        got: list[str] = []
        while len(got) < args.per_label:
            prompt = (
                f"Write 10 varied, realistic one-sentence descriptions of AI systems, as a product manager would "
                f"describe them, that fall under: {meaning}. Vary industries, wording and length; avoid legal terms. "
                f"Don't repeat these: {got[-10:]}"
            )
            batch = complete_structured(
                provider, [{"role": "user", "content": prompt}], Batch, temperature=0.9
            )
            got += [d.strip() for d in batch.descriptions if d.strip() and d.strip() not in got]
            print(f"{label}: {len(got)}/{args.per_label}")
        rows += [{"text": d, "label": label} for d in got[: args.per_label]]
    with open("data/training/annex3.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "label"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to data/training/annex3.csv. Now review them by hand!")


if __name__ == "__main__":
    main()
