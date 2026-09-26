.PHONY: help setup up down models migrate ingest dev worker test test-phase lint typecheck eval-retrieval evals train drift load ui

help:          ## Show commands
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup:         ## Install everything for local development
	uv sync --all-extras
	uv run pre-commit install
	cp -n .env.example .env || true

up:            ## Start Postgres, Redis, Ollama, MLflow, Prometheus, Grafana (+ api, worker)
	docker compose up -d --build

down:          ## Stop the stack
	docker compose down

models:        ## Pull the Ollama chat + embedding models (first run)
	docker compose exec ollama ollama pull $${OLLAMA_MODEL:-llama3.1:8b}
	docker compose exec ollama ollama pull nomic-embed-text

migrate:       ## Apply database migrations
	uv run python -m app.db

ingest:        ## Download and ingest the AI Act (add FILE=data/raw/ai_act.html to use a saved copy)
	uv run python scripts/ingest.py $(if $(FILE),--file $(FILE),)

dev:           ## Run the API locally with auto-reload
	uv run uvicorn app.main:app --reload

worker:        ## Run a background worker locally
	uv run rq worker assessments --url $${REDIS_URL:-redis://localhost:6379/0}

test:          ## Run all unit tests (no services needed)
	uv run pytest -q

test-phase:    ## Run one phase's tests: make test-phase P=2
	uv run pytest -q tests/test_phase$(P)_*.py

integration:   ## Integration tests against the running stack (make up first)
	uv run pytest -q -m integration

lint:          ## Lint and format check
	uv run ruff check . && uv run ruff format --check .

typecheck:     ## Static type check
	uv run mypy app --ignore-missing-imports

eval-retrieval: ## Retrieval metrics (recall@k, MRR) on evals/retrieval_eval.jsonl
	uv run python scripts/eval_retrieval.py

evals:         ## End-to-end assessment evals on evals/scenarios.jsonl
	uv run python evals/run_evals.py

train:         ## Train, log to MLflow and (if better) promote the Annex III classifier
	uv run python scripts/train_classifier.py

drift:         ## Drift check of recent inputs vs training data
	uv run python scripts/drift_check.py

load:          ## Load test with Locust (web UI on :8089)
	uv run locust -f loadtest/locustfile.py --host http://localhost:8000

ui:            ## Start the Streamlit UI
	docker compose --profile ui up -d ui
