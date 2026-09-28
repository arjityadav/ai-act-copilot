"""The FastAPI application (given).

uvicorn app.main:app --reload            (or: make dev)
docs at http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from app.api import routes_assessments, routes_chat, routes_health
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
log = logging.getLogger("copilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.store == "postgres" and s.env != "test":
        try:
            from app.db import migrate

            migrate(s.database_url)
        except Exception as e:  # the API still starts; /ready reports the problem
            log.warning(f"migrations not applied: {e}")
    if s.env == "prod" and not s.api_key:
        raise RuntimeError("API_KEY must be set in production")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="EU AI Act Compliance Copilot",
        version="0.1.0",
        lifespan=lifespan,
        description="RAG over the EU AI Act + multi-agent risk classification, obligations and gap analysis. "
        "Decision support, not legal advice.",
    )
    app.include_router(routes_health.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_assessments.router)

    try:  # Phase 8: metrics middleware + /metrics endpoint
        from app.observability import metrics

        app.middleware("http")(metrics.metrics_middleware)

        @app.get("/metrics", include_in_schema=False)
        def metrics_endpoint():
            body, ctype = metrics.metrics_response()
            return Response(content=body, media_type=ctype)
    except ImportError:
        log.info("prometheus-client not installed; /metrics disabled")
    return app


app = create_app()
