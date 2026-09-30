"""Health checks (given): /health for liveness (process is up), /ready for readiness (dependencies reachable).
/version reports the deployed git commit (APP_VERSION is set by deploy/deploy.sh; CD waits for it)."""

import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import settings_dep, store_dep

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/version")
def version():
    return {"version": os.environ.get("APP_VERSION", "dev")}


@router.get("/ready")
def ready(settings=Depends(settings_dep)):
    checks = {}
    try:
        checks["chunks"] = store_dep().count()
        checks["store"] = "ok"
    except Exception as e:
        checks["store"] = f"error: {type(e).__name__}"
    if settings.job_mode == "queue":
        try:
            import redis

            redis.Redis.from_url(settings.redis_url, socket_timeout=2).ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {type(e).__name__}"
    ok = all(v == "ok" or isinstance(v, int) for v in checks.values())
    return JSONResponse(status_code=200 if ok else 503, content={"ready": ok, **checks})
