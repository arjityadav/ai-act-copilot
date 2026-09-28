"""Load test (Phase 8).  make load  -> open http://localhost:8089, e.g. 20 users, spawn rate 2.

Measure p50/p95 latency and error rate for /chat and assessment creation; find where it breaks
(LLM rate limits, worker concurrency, DB connections). Record results in docs/RUNBOOK.md.
"""

import os
import random

from locust import HttpUser, between, task

QUESTIONS = [
    "Which AI practices are prohibited?",
    "Do I have to tell users they are talking to a chatbot?",
    "Is CV screening high-risk?",
    "What does a deployer of a high-risk AI system have to do?",
    "When do the high-risk obligations apply?",
]
HEADERS = {"X-API-Key": os.environ.get("API_KEY", "")}


class CopilotUser(HttpUser):
    wait_time = between(1, 4)

    @task(5)
    def chat(self):
        self.client.post("/chat", json={"question": random.choice(QUESTIONS)}, headers=HEADERS, name="/chat")

    @task(1)
    def assessment(self):
        r = self.client.post(
            "/assessments",
            headers=HEADERS,
            name="/assessments",
            json={"description": "A chatbot that answers customer questions about our online shop."},
        )
        if r.status_code == 202:
            self.client.get(f"/assessments/{r.json()['id']}", headers=HEADERS, name="/assessments/{id}")

    @task(2)
    def health(self):
        self.client.get("/health")
