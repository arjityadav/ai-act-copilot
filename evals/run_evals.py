"""End-to-end assessment evals (Phase 7).   make evals

Runs the intake -> screen -> classify steps for each scenario in evals/scenarios.jsonl and
scores the classification with app/llmops/evals.py. Clarifying questions are skipped: the eval
measures the classification the system makes from the description alone.

    python evals/run_evals.py                       # Postgres store + Ollama embeddings (make up, make ingest)
    python evals/run_evals.py --in-memory           # index data/corpus/ai_act.txt in memory (CI)
    python evals/run_evals.py --min-pass-rate 0.8   # exit code 1 below the threshold (CI gate)
    python evals/run_evals.py --only s01,s07        # a subset
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import classifier, intake, rules  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.llm.provider import get_provider  # noqa: E402
from app.llmops.evals import score_assessment, summarise  # noqa: E402


def build_index(in_memory: bool):
    s = get_settings()
    if not in_memory:
        from app.retrieval.embed import OllamaEmbedder
        from app.retrieval.store import get_store
        return get_store(s), OllamaEmbedder(s)
    from app.ingest.pipeline import ingest_text
    from app.retrieval.embed import HashEmbedder
    from app.retrieval.store import InMemoryStore
    store, emb = InMemoryStore(), HashEmbedder(512)
    ingest_text(open("data/corpus/ai_act.txt", encoding="utf-8").read(), store, emb)
    return store, emb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-memory", action="store_true")
    ap.add_argument("--min-pass-rate", type=float, default=None)
    ap.add_argument("--only", default="")
    ap.add_argument("--report", default="evals/results/report.md")
    args = ap.parse_args()

    store, emb = build_index(args.in_memory)
    provider = get_provider()
    cases = [json.loads(line) for line in open("evals/scenarios.jsonl", encoding="utf-8") if line.strip()]
    if args.only:
        cases = [c for c in cases if c["id"] in args.only.split(",")]

    rows, scores, t0 = [], [], time.perf_counter()
    for c in cases:
        try:
            profile = intake.extract_profile(c["description"], provider)
            flags = rules.screen(profile)
            a = classifier.classify(profile, flags, store, emb, provider).model_dump()
        except Exception as e:
            a = {"category": f"error: {type(e).__name__}", "citations": [], "annex_iii_area": "none",
                 "transparency_obligations": False, "confidence": "low"}
        sc = score_assessment(c["expected"], a)
        scores.append(sc)
        rows.append((c["id"], c["expected"]["category"], a["category"], a.get("annex_iii_area"), sc))
        print(f"{'✓' if sc['passed'] else '✗'} {c['id']}  expected {c['expected']['category']:<13} got {a['category']:<13} "
              f"area {a.get('annex_iii_area')}  citations {a.get('citations')}")

    summary = summarise(scores)
    elapsed = time.perf_counter() - t0
    print(f"\n{json.dumps(summary, indent=2)}\n{elapsed:.0f}s · provider {provider.name}/{provider.model}")

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(f"## Scenario evals · {provider.name}/{provider.model}\n\n")
        f.write(f"**Pass rate {summary['pass_rate']:.0%}** · category accuracy {summary['category_accuracy']} · "
                f"mean citation recall {summary['mean_citation_recall']} · n = {summary['n']}\n\n")
        f.write("| id | expected | got | area | passed |\n|---|---|---|---|---|\n")
        for cid, exp, got, area, sc in rows:
            f.write(f"| {cid} | {exp} | {got} | {area} | {'✅' if sc['passed'] else '❌'} |\n")
    if args.min_pass_rate is not None and summary["pass_rate"] < args.min_pass_rate:
        print(f"FAIL: pass rate {summary['pass_rate']:.0%} is below {args.min_pass_rate:.0%}")
        sys.exit(1)


if __name__ == "__main__":
    main()
