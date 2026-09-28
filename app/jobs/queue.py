"""Running assessments in the background (given).

JOB_MODE=queue  -> Redis + RQ: the API enqueues, `rq worker assessments` (docker compose service) runs it.
JOB_MODE=inline -> run immediately in the API process (tests, quick local dev).
Long LLM pipelines never run inside the request: the API returns 202 + an id at once (notes Day 86).
"""

from __future__ import annotations

import traceback

from app.config import get_settings


def build_deps(repo, aid, settings=None):
    from app.agents.graph import PipelineDeps
    from app.api import deps as api_deps

    ml = None
    try:
        from app.mlops.serve import load_classifier

        ml = load_classifier(settings or get_settings())
    except Exception:
        ml = None  # the ML pre-screen is optional until Phase 6 is done
    return PipelineDeps(
        provider=api_deps.provider_dep(),
        store=api_deps.store_dep(),
        embedder=api_deps.embedder_dep(),
        events=lambda stage, msg: repo.add_event(aid, stage, msg),
        ml_classifier=ml,
    )


def run_assessment(aid: str, repo=None, deps=None):
    """The job: load input, run the graph, save the result. Safe to call from RQ or inline."""
    from app.agents.graph import run_pipeline
    from app.jobs.repo import get_repo

    repo = repo or get_repo(get_settings())
    item = repo.get(aid)
    repo.update(aid, status="running")
    try:
        deps = deps or build_deps(repo, aid)
        payload = item["input"]
        final = run_pipeline(
            {
                "assessment_id": aid,
                "description": payload["description"],
                "answers": payload.get("answers") or {},
                "practices": payload.get("practices") or {},
            },
            deps,
        )
        if final.get("status") == "needs_input":
            repo.update(
                aid,
                status="needs_input",
                result={"questions": final.get("questions", []), "profile": final["profile"].model_dump()},
            )
            return
        result = {
            "profile": final["profile"].model_dump(),
            "assessment": final["assessment"].model_dump(),
            "obligations": [o.model_dump() for o in final["obligations"]],
            "gaps": [g.model_dump() for g in final["gaps"]],
            "report": final["report"].model_dump(),
            "verification": final["verification"].model_dump(),
            "ml_prediction": final.get("ml_prediction"),
        }
        repo.update(aid, status="done", result=result)
        repo.add_event(aid, "done", "Assessment complete")
    except Exception as e:
        repo.update(aid, status="failed", error=f"{type(e).__name__}: {e}")
        repo.add_event(aid, "failed", traceback.format_exc(limit=3))


def enqueue(aid: str, settings=None, repo=None, deps=None):
    s = settings or get_settings()
    if s.job_mode == "inline":
        run_assessment(aid, repo=repo, deps=deps)
        return
    import redis
    from rq import Queue

    Queue("assessments", connection=redis.Redis.from_url(s.redis_url)).enqueue(
        run_assessment, aid, job_timeout=900
    )
