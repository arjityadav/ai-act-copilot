"""Assessment storage (given): in memory for tests/dev, Postgres in production."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime


class InMemoryRepo:
    def __init__(self):
        self.items, self.events = {}, {}

    def create(self, payload: dict) -> str:
        aid = str(uuid.uuid4())
        self.items[aid] = {"id": aid, "status": "queued", "input": payload, "result": None, "error": None}
        self.events[aid] = []
        return aid

    def get(self, aid):
        return self.items.get(aid)

    def update(self, aid, **fields):
        self.items[aid].update(fields)

    def add_event(self, aid, stage, message):
        self.events[aid].append(
            {
                "id": len(self.events[aid]) + 1,
                "stage": stage,
                "message": message,
                "at": datetime.now(UTC).isoformat(),
            }
        )

    def events_after(self, aid, after_id=0):
        return [e for e in self.events.get(aid, []) if e["id"] > after_id]


class PostgresRepo:
    def __init__(self, url):
        import psycopg

        self._psycopg, self.url = psycopg, url

    def _c(self):
        return self._psycopg.connect(self.url, autocommit=True)

    def create(self, payload):
        aid = str(uuid.uuid4())
        with self._c() as c:
            c.execute(
                "INSERT INTO assessments (id, status, input) VALUES (%s, 'queued', %s)",
                (aid, json.dumps(payload)),
            )
        return aid

    def get(self, aid):
        try:
            uuid.UUID(str(aid))
        except ValueError:
            return None  # not a valid id -> "not found" (404), not a database error (500)
        with self._c() as c:
            r = c.execute(
                "SELECT id, status, input, result, error FROM assessments WHERE id = %s", (aid,)
            ).fetchone()
        return (
            None
            if r is None
            else {"id": str(r[0]), "status": r[1], "input": r[2], "result": r[3], "error": r[4]}
        )

    def update(self, aid, **fields):
        sets, vals = [], []
        for k, v in fields.items():
            sets.append(f"{k} = %s")
            vals.append(json.dumps(v) if k in ("result", "input") and v is not None else v)
        with self._c() as c:
            c.execute(
                f"UPDATE assessments SET {', '.join(sets)}, updated_at = now() WHERE id = %s", (*vals, aid)
            )

    def add_event(self, aid, stage, message):
        with self._c() as c:
            c.execute(
                "INSERT INTO assessment_events (assessment_id, stage, message) VALUES (%s, %s, %s)",
                (aid, stage, message),
            )

    def events_after(self, aid, after_id=0):
        with self._c() as c:
            rows = c.execute(
                "SELECT id, stage, message, created_at FROM assessment_events WHERE assessment_id = %s "
                "AND id > %s ORDER BY id",
                (aid, after_id),
            ).fetchall()
        return [{"id": r[0], "stage": r[1], "message": r[2], "at": r[3].isoformat()} for r in rows]


_MEMORY_REPO = InMemoryRepo()


def get_repo(settings):
    return _MEMORY_REPO if settings.store == "memory" else PostgresRepo(settings.database_url)
