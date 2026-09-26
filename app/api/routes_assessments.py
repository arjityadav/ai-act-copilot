"""Assessment endpoints (given).

POST /assessments                {description, practices?}     -> 202 {id, status}
GET  /assessments/{id}           status, questions or result
POST /assessments/{id}/answers   {answers: {question: answer}}  -> starts a new run with the answers (human in the loop)
GET  /assessments/{id}/events    server-sent events with progress, until done/failed/needs_input
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.api.deps import assessments_dep, require_api_key, settings_dep
from app.jobs.queue import enqueue
from app.rag.guardrails import check_input, redact_pii

router = APIRouter(prefix="/assessments", tags=["assessments"], dependencies=[Depends(require_api_key)])


class AssessmentRequest(BaseModel):
    description: str = Field(description="Describe the AI system: what it does, who uses it, whose decisions it affects")
    practices: dict[str, str] = Field(default_factory=dict, description='Obligation id -> "yes" | "partial" | "no"')


class AnswersRequest(BaseModel):
    answers: dict[str, str]


def _start(payload, background, settings, repo):
    aid = repo.create(payload)
    if settings.job_mode == "inline":
        background.add_task(enqueue, aid, settings, repo)
    else:
        enqueue(aid, settings, repo)
    return aid


@router.post("", status_code=202)
def create(req: AssessmentRequest, background: BackgroundTasks, settings=Depends(settings_dep), repo=Depends(assessments_dep)):
    guard = check_input(req.description, settings.max_input_chars)
    if not guard.ok:
        raise HTTPException(400, detail=guard.reason)
    aid = _start({"description": redact_pii(req.description), "practices": req.practices}, background, settings, repo)
    return {"id": aid, "status": "queued"}


@router.get("/{aid}")
def get(aid: str, repo=Depends(assessments_dep)):
    item = repo.get(aid)
    if item is None:
        raise HTTPException(404, detail="Assessment not found")
    return item


@router.post("/{aid}/answers", status_code=202)
def answer(aid: str, req: AnswersRequest, background: BackgroundTasks, settings=Depends(settings_dep),
           repo=Depends(assessments_dep)):
    item = repo.get(aid)
    if item is None:
        raise HTTPException(404, detail="Assessment not found")
    if item["status"] != "needs_input":
        raise HTTPException(409, detail=f"Assessment is {item['status']}, not waiting for answers")
    payload = {**item["input"], "answers": {k: redact_pii(v) for k, v in req.answers.items()}}
    new_id = _start(payload, background, settings, repo)
    return {"id": new_id, "status": "queued", "previous": aid}


@router.get("/{aid}/events")
async def events(aid: str, repo=Depends(assessments_dep)):
    if repo.get(aid) is None:
        raise HTTPException(404, detail="Assessment not found")

    async def stream():
        last = 0
        while True:
            for e in repo.events_after(aid, last):
                last = e["id"]
                yield {"event": e["stage"], "data": json.dumps(e)}
            if repo.get(aid)["status"] in ("done", "failed", "needs_input"):
                yield {"event": "end", "data": json.dumps({"status": repo.get(aid)["status"]})}
                return
            await asyncio.sleep(0.5)

    return EventSourceResponse(stream())
