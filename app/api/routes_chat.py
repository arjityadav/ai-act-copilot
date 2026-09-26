"""PHASE 3 · The Q&A endpoints.

POST /chat          JSON answer with sources           <- you write this one
GET  /chat/stream   server-sent events (given)
POST /feedback      thumbs up/down (given)

Read first: notes Day 64 (serving RAG), FastAPI tutorial (path operations, request bodies, HTTPException).
"""

from __future__ import annotations

import json
import uuid  # noqa: F401  (you'll need it for trace ids)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.api.deps import cache_dep, embedder_dep, provider_dep, require_api_key, settings_dep, store_dep
from app.llmops.prompts import get_prompt
from app.rag.answer import REFUSAL, answer_question, build_user_message
from app.rag.guardrails import check_input, redact_pii
from app.retrieval.search import hybrid_search

router = APIRouter(tags=["chat"], dependencies=[Depends(require_api_key)])


class ChatRequest(BaseModel):
    question: str = Field(description="A question about the EU AI Act")


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    citations_valid: bool
    refused: bool
    prompt_version: str
    cached: bool = False
    trace_id: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    settings=Depends(settings_dep),
    store=Depends(store_dep),
    embedder=Depends(embedder_dep),
    provider=Depends(provider_dep),
    cache=Depends(cache_dep),
):
    """
    1. guard = check_input(req.question, settings.max_input_chars); if not ok -> HTTPException(400, detail=guard.reason)
    2. question = redact_pii(req.question)
    3. trace_id = uuid.uuid4().hex
    4. (Phase 7) if cache is not None and cache.get(question) returns a dict: return ChatResponse(**that, cached=True, trace_id=trace_id)
    5. result = answer_question(question, store, embedder, provider)   (import it from app.rag.answer)
    6. build the ChatResponse from the RagAnswer fields; (Phase 7) cache.put(question, <response dict without trace_id/cached>)
       only when the answer isn't a refusal and citations are valid.
    """
    guard = check_input(req.question, settings.max_input_chars)
    if not guard.ok:
        raise HTTPException(400, detail=guard.reason)
    question = redact_pii(req.question)
    trace_id = uuid.uuid4().hex
    # TODO(Phase 7): restore once SemanticCache.get/put are implemented
    # if cache is not None:
    #     cached_response = cache.get(question)
    #     if cached_response is not None:
    #         return ChatResponse(**cached_response, cached=True, trace_id=trace_id)
    result = answer_question(question, store, embedder, provider)
    response_dict = {
        "answer": result.answer,
        "sources": result.sources,
        "citations_valid": result.citations_valid,
        "refused": result.refused,
        "prompt_version": result.prompt_version,
        "cached": False,
        "trace_id": trace_id,
    }
    # if not result.refused and result.citations_valid and cache is not None:
    #     cache.put(question, {k: v for k, v in response_dict.items() if k not in ["trace_id", "cached"]})
    return ChatResponse(**response_dict)


@router.get("/chat/stream")
def chat_stream(
    question: str,
    settings=Depends(settings_dep),
    store=Depends(store_dep),
    embedder=Depends(embedder_dep),
    provider=Depends(provider_dep),
):
    """Streams events: `sources` (JSON list), many `token`, then `done`. (Given.)"""
    guard = check_input(question, settings.max_input_chars)
    if not guard.ok:
        raise HTTPException(400, detail=guard.reason)
    question = redact_pii(question)
    chunks = hybrid_search(question, store, embedder, k=6)
    prompt = get_prompt("rag_answer")

    def events():
        yield {
            "event": "sources",
            "data": json.dumps(
                [{"n": i, "citation": c.citation, "chunk_id": c.id} for i, c in enumerate(chunks, 1)]
            ),
        }
        for piece in provider.stream(
            [{"role": "user", "content": build_user_message(question, chunks)}], system=prompt.system
        ):
            yield {"event": "token", "data": piece}
        yield {
            "event": "done",
            "data": json.dumps({"prompt_version": prompt.version, "refusal_text": REFUSAL}),
        }

    return EventSourceResponse(events())


class FeedbackRequest(BaseModel):
    target: str = Field(description='"chat:<trace_id>" or "assessment:<id>"')
    rating: int = Field(ge=-1, le=1)
    comment: str | None = None


FEEDBACK: list[dict] = []  # in-memory fallback; stored in Postgres when available


@router.post("/feedback", status_code=201)
def feedback(req: FeedbackRequest, settings=Depends(settings_dep)):
    if settings.store == "postgres":
        import psycopg

        with psycopg.connect(settings.database_url, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO feedback (target, rating, comment) VALUES (%s, %s, %s)",
                (req.target, req.rating, req.comment),
            )
    else:
        FEEDBACK.append(req.model_dump())
    return {"stored": True}
