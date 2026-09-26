# Runbook

*Operational guide. Fill in the blanks as you deploy and load-test (Phase 8).*

## Service overview
| Component | Where | Health |
|---|---|---|
| API | ______ | `GET /health` (liveness), `GET /ready` (DB + Redis) |
| Worker | ______ | queue length in Redis (`rq info`) |
| Postgres + pgvector | ______ | `/ready` → store ok |
| Redis | ______ | `/ready` → redis ok |
| Ollama (embeddings) | ______ | `GET /api/tags` |
| Dashboards | Grafana ______ · Langfuse ______ · MLflow ______ | |

## SLOs (targets)
- Availability of `/chat`: 99.5% monthly.
- p95 `/chat` latency: < ____ s. Median assessment duration: < ____ min.
- LLM cost: < $____ per 1,000 chat questions; < $____ per assessment.

## Deploy and rollback
- Deploy: merge to `main` → CI → CD builds `ghcr.io/<you>/ai-act-copilot:<sha>`, deploys, smoke-tests `/health`.
- Rollback: redeploy the previous SHA (Render: Manual Deploy → previous image; or run the deploy hook with `imgURL=...:<previous-sha>`).
- Migrations: forward-only, additive; run automatically at API start-up.

## Common incidents
| Symptom | Likely cause | Action |
|---|---|---|
| `/ready` 503, store error | DB down / credentials | Check DB status, `DATABASE_URL`, connection limits |
| Assessments stuck in `queued` | Worker down or Redis unreachable | Restart worker; check `rq info`; check `REDIS_URL` |
| Many `failed` assessments | LLM provider errors / rate limits | Check provider status; fallback chain in `LLM_PROVIDERS`; lower worker concurrency |
| Answers flagged "citations not valid" | Retrieval regression or prompt change | Run `make eval-retrieval` and `make evals`; compare prompt versions |
| Cost spike | Traffic spike, cache disabled, prompt got longer | Grafana cost panel by provider; `llm_calls` by prompt_version |
| Drift issue opened | Input distribution changed | Review recent inputs, label, `make train` |

## Load test results (Locust)
| Users | RPS | p50 | p95 | Errors | Bottleneck |
|---|---|---|---|---|---|
| | | | | | |

## Threat model (OWASP LLM Top 10, short)
| Risk | Where | Mitigation |
|---|---|---|
| Prompt injection | descriptions, questions | pattern screen, data-in-tags, no write tools, verifier |
| Sensitive information disclosure | inputs, logs | PII redaction, retention limits, API key |
| Improper output handling | report Markdown in UI | render as Markdown only, no HTML execution |
| Excessive agency | agents | agents have read-only retrieval, no external actions |
| Unbounded consumption | chat, assessments | input size limit, rate limits, max write attempts, timeouts |
| Misinformation | answers, reports | citations verified, disclaimer, human review |
