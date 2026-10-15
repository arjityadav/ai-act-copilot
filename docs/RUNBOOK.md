# Runbook

Operational guide for the production deployment. Setup steps are in [DEPLOY.md](DEPLOY.md).

## Service overview
Production runs on one Oracle Cloud Ampere VM (Frankfurt) with `docker-compose.prod.yml`.
Prefix commands with `dcp` = `docker compose -f docker-compose.prod.yml --env-file .env.prod`.

| Component | Where | Health |
|---|---|---|
| Caddy (TLS, routing) | ports 80/443, `deploy/Caddyfile` | site reachable over HTTPS; `dcp logs caddy` |
| Web UI (Streamlit) | `https://ai-act-copilot.duckdns.org/` | container healthcheck on `/_stcore/health` |
| API (FastAPI) | `/docs`, `/chat`, `/assessments`, … | `GET /health` (liveness), `GET /ready` (store + Redis), `GET /version` (deployed commit) |
| Worker (RQ) | `worker` container | container healthcheck (Redis ping); queue length with `rq info` |
| Postgres + pgvector | `db` container, internal only | `/ready` → `store: ok` |
| Redis (AOF persistence) | `redis` container, internal only | `/ready` → `redis: ok` |
| Ollama (embeddings) | `ollama` container, internal only | `dcp exec ollama ollama list` shows `nomic-embed-text` |
| LLM | Groq API (`openai/gpt-oss-120b`) | provider status page; HTTP 429 in worker/API logs = rate limit |
| Dashboards | local development only (Prometheus, Grafana, MLflow in `docker-compose.yml`) | — |

## Targets (not yet verified under load)
- p95 `/chat` latency < 10 s; median assessment duration < 5 min.
- LLM cost: $0 on Groq's free tier; capacity is bounded by its limits (8k tokens/min, 200k tokens/day).

## Deploy and rollback
- **Deploy:** merge to `main` → CI → the server's systemd timer (every 2 min) deploys commits whose CI
  succeeded (`deploy/deploy.sh`), waits for healthy containers and `/version` = commit, otherwise
  **rolls back automatically**. The GitHub `CD` workflow waits for `/version` and smoke-tests the site.
- **Watch:** `journalctl -u ai-act-deploy -f`. **Deploy now:** `sudo systemctl start ai-act-deploy.service`.
- **Manual rollback:** `git reset --hard <previous-sha> && dcp up -d --build && dcp up -d --force-recreate caddy`
  (and push a revert to `main`, or the timer will deploy the newer commit again).
- **Failed commit:** recorded in `.deploy-failed` and not retried until a newer commit arrives; delete
  the file to force a retry.
- **Migrations:** forward-only, additive; run automatically at API start-up.

## Common incidents
| Symptom | Likely cause | Action |
|---|---|---|
| Site unreachable (timeout) | VM down, or a firewall layer (security list or iptables) | Oracle console → instance state; check ingress rules for 80/443 and `sudo iptables -L INPUT -n` |
| HTTPS certificate error | DNS not pointing at the VM, or port 80 blocked | `dig +short <domain>`; `dcp logs caddy` |
| `/ready` 503, store error | DB down / credentials | `dcp ps`; `DATABASE_URL`, `POSTGRES_PASSWORD` in `.env.prod` |
| Assessments stuck in `queued` | worker down or Redis unreachable | `dcp restart worker`; `rq info` |
| Assessment stuck in `running` | worker killed mid-job | mark it failed / re-submit (no automatic reconciler yet) |
| Many `failed` assessments or slow answers | Groq rate limits (429) or provider outage | wait for the per-minute/day limit to reset; add a fallback provider to `LLM_PROVIDERS` |
| Answers flagged "citations not valid" | retrieval regression or prompt change | `make eval-retrieval` and `make evals`; compare prompt versions |
| SSH times out | home IP changed (SSH is restricted to one IP) | update the port-22 ingress rule; `echo $SSH_CLIENT` shows the IP the server sees |
| Drift issue opened | input distribution changed | review recent inputs, label, `make train` |

## Load test results (Locust)
Not run against production yet (`make load`). Free-tier LLM limits make the LLM the expected bottleneck.

| Users | RPS | p50 | p95 | Errors | Bottleneck |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Threat model (OWASP LLM Top 10, short)
| Risk | Where | Mitigation |
|---|---|---|
| Prompt injection | descriptions, questions | pattern screen, data in XML tags, no write tools, verifier |
| Sensitive information disclosure | inputs, logs | PII redaction before retrieval and LLM calls, API key, internal-only DB/Redis |
| Improper output handling | report Markdown in UI | rendered as Markdown only, no HTML execution |
| Excessive agency | agents | fixed workflow, read-only retrieval, no external actions |
| Unbounded consumption | chat, assessments | input size limit, max write attempts, timeouts, provider rate limits |
| Misinformation | answers, reports | citations verified in code, rule checks, disclaimer appended in code, human review |
