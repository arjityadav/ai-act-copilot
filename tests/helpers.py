"""Shared test helpers: fakes and a small in-memory corpus. No network, no services."""

from __future__ import annotations

import json
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("STORE", "memory")
os.environ.setdefault("JOB_MODE", "inline")

from app.llm.provider import FakeProvider  # noqa: E402,F401
from app.retrieval.embed import HashEmbedder  # noqa: E402
from app.retrieval.store import Chunk, InMemoryStore  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def sample_text() -> str:
    with open(os.path.join(FIXTURES, "act_sample.txt"), encoding="utf-8") as f:
        return f.read()


def make_chunk(provision_id, text, title="Title", idx=0):
    kind = "annex" if provision_id.startswith("annex") else "article"
    number = provision_id.split("-", 1)[1].upper() if kind == "annex" else provision_id.split("-", 1)[1]
    return Chunk(
        id=f"{provision_id}-{idx}",
        provision_id=provision_id,
        kind=kind,
        number=number,
        title=title,
        text=text,
    )


def small_corpus():
    """An InMemoryStore with hand-written chunks (doesn't depend on your Phase 1 code)."""
    chunks = [
        make_chunk(
            "art-5",
            "EU AI Act · Article 5 · Prohibited AI practices\n\nsocial scoring manipulative techniques "
            "emotion recognition workplace untargeted scraping facial images prohibited",
            "Prohibited AI practices",
        ),
        make_chunk(
            "art-6",
            "EU AI Act · Article 6 · Classification rules for high-risk AI systems\n\nhigh-risk Annex III "
            "safety component Annex I classification rules",
            "Classification rules for high-risk AI systems",
        ),
        make_chunk(
            "art-50",
            "EU AI Act · Article 50 · Transparency obligations\n\ninform persons interacting with an AI system "
            "chatbot synthetic content marked deep fakes disclose",
            "Transparency obligations",
        ),
        make_chunk(
            "art-53",
            "EU AI Act · Article 53 · Obligations for providers of general-purpose AI models\n\ntechnical "
            "documentation downstream providers copyright policy training content summary",
            "GPAI obligations",
        ),
        make_chunk(
            "annex-iii",
            "EU AI Act · Annex III · High-risk AI systems\n\nemployment recruitment selection filter job "
            "applications evaluate candidates creditworthiness credit score insurance pricing education "
            "admission proctoring biometrics",
            "High-risk AI systems referred to in Article 6(2)",
        ),
        make_chunk(
            "art-99",
            "EU AI Act · Article 99 · Penalties\n\nfines up to EUR 35 000 000 or 7 % turnover",
            "Penalties",
        ),
    ]
    store, emb = InMemoryStore(), HashEmbedder(256)
    store.upsert(chunks, emb.embed([c.text for c in chunks]))
    return store, emb


def profile_json(**overrides) -> str:
    base = {
        "name": "CV Ranker",
        "purpose": "Screens CVs and ranks job applicants for recruiters",
        "sector": "HR / recruitment",
        "role": "provider",
        "affected_persons": "job applicants",
        "decisions_about_people": True,
        "uses_biometrics": False,
        "emotion_recognition": False,
        "interacts_with_people": False,
        "generates_content": False,
        "is_general_purpose_model": False,
        "safety_component_of_product": False,
        "annex_iii_area": "employment",
        "missing_info": [],
    }
    base.update(overrides)
    return json.dumps(base)


def assessment_json(**overrides) -> str:
    base = {
        "category": "high_risk",
        "annex_iii_area": "employment",
        "role": "provider",
        "transparency_obligations": False,
        "reasoning": "Recruitment is listed in Annex III point 4, so Article 6(2) applies.",
        "citations": ["art-6", "annex-iii"],
        "confidence": "high",
        "flags": [],
    }
    base.update(overrides)
    return json.dumps(base)
