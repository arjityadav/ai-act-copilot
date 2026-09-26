-- 001: core schema. Applied by `make migrate` (app/db.py) or automatically on API start-up.
CREATE EXTENSION IF NOT EXISTS vector;

-- Legal corpus: one row per chunk of an article or annex
CREATE TABLE IF NOT EXISTS chunks (
    id            TEXT PRIMARY KEY,
    provision_id  TEXT NOT NULL,
    kind          TEXT NOT NULL,
    number        TEXT NOT NULL,
    title         TEXT NOT NULL,
    text          TEXT NOT NULL,
    chapter       TEXT,
    content_hash  TEXT NOT NULL,
    embedding     vector(768),          -- must match EMBED_DIM (nomic-embed-text = 768)
    tsv           tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || text)) STORED,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_provision ON chunks (provision_id);

-- Assessments (multi-agent runs) and their progress events
CREATE TABLE IF NOT EXISTS assessments (
    id          UUID PRIMARY KEY,
    status      TEXT NOT NULL,           -- queued | running | needs_input | done | failed
    input       JSONB NOT NULL,
    result      JSONB,
    error       TEXT,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS assessment_events (
    id             BIGSERIAL PRIMARY KEY,
    assessment_id  UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    stage          TEXT NOT NULL,
    message        TEXT NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_by_assessment ON assessment_events (assessment_id, id);

-- LLMOps: every model call, and user feedback
CREATE TABLE IF NOT EXISTS llm_calls (
    id              BIGSERIAL PRIMARY KEY,
    trace_id        TEXT,
    agent           TEXT,
    provider        TEXT,
    model           TEXT,
    prompt_name     TEXT,
    prompt_version  TEXT,
    input_tokens    INT,
    output_tokens   INT,
    latency_ms      INT,
    cost_usd        NUMERIC(12, 6),
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS feedback (
    id          BIGSERIAL PRIMARY KEY,
    target      TEXT NOT NULL,            -- "chat:<trace_id>" or "assessment:<id>"
    rating      SMALLINT NOT NULL,        -- 1 = helpful, -1 = not helpful
    comment     TEXT,
    created_at  timestamptz NOT NULL DEFAULT now()
);
