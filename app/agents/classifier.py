"""PHASE 4 · Classifier agent: plan searches, read the law, classify with citations, check itself.

Read first: notes Days 67–69 (agents, tool design), 59 (grounding), supplement S7.

This is an agentic workflow rather than a free-roaming agent: the steps are fixed (plan ->
retrieve -> decide -> verify), which makes it predictable, testable and cheap, while the LLM
does the reading and judgement inside each step.
"""

from __future__ import annotations

import json  # noqa: F401  (useful for building the prompt)

from app.agents.schemas import RiskAssessment, SystemProfile
from app.llm.structured import complete_structured
from app.llmops.prompts import get_prompt
from app.retrieval.search import hybrid_search
from app.retrieval.store import Chunk

AREA_QUERIES = {
    "biometrics": "Annex III biometrics remote biometric identification categorisation emotion recognition",
    "critical_infrastructure": "Annex III critical infrastructure safety components",
    "education": "Annex III education vocational training admission evaluation proctoring",
    "employment": "Annex III employment recruitment selection workers management",
    "essential_services": "Annex III essential private and public services creditworthiness insurance benefits",
    "law_enforcement": "Annex III law enforcement",
    "migration": "Annex III migration asylum border control",
    "justice_democracy": "Annex III administration of justice democratic processes",
}


def plan_queries(profile: SystemProfile, flags: list[str]) -> list[str]:
    """Search queries to run, in this order, without duplicates:
    1. "Article 5 prohibited AI practices"
    2. "Article 6 classification rules for high-risk AI systems"
    3. AREA_QUERIES[area] for the profile's annex_iii_area (if it's a key of AREA_QUERIES)
    4. "Article 50 transparency obligations" if any flag starts with "transparency:"
    5. "Article 53 obligations for providers of general-purpose AI models" if "gpai:model" in flags
    6. profile.purpose  (the system's own words, to catch anything the rules missed)
    """
    queries = [
        "Article 5 prohibited AI practices",
        "Article 6 classification rules for high-risk AI systems",
    ]
    if profile.annex_iii_area in AREA_QUERIES:
        queries.append(AREA_QUERIES[profile.annex_iii_area])
    if any(flag.startswith("transparency:") for flag in flags):
        queries.append("Article 50 transparency obligations")
    if "gpai:model" in flags:
        queries.append("Article 53 obligations for providers of general-purpose AI models")
    queries.append(profile.purpose)
    return list(dict.fromkeys(queries))  # remove duplicates while preserving order


def gather_context(
    queries: list[str], store, embedder, per_query: int = 4, max_chunks: int = 14
) -> list[Chunk]:
    """Run hybrid_search(q, store, embedder, k=per_query) for each query; keep chunks in order of
    first appearance without duplicate ids; stop at max_chunks."""
    chunks: list[Chunk] = []
    seen_ids: set[str] = set()
    for q in queries:
        for chunk in hybrid_search(q, store, embedder, k=per_query):
            if chunk.id not in seen_ids:  # was chunk.provision_id
                chunks.append(chunk)
                seen_ids.add(chunk.id)  # was chunk.provision_id
                if len(chunks) >= max_chunks:
                    return chunks
    return chunks


def classify(profile: SystemProfile, flags: list[str], store, embedder, provider) -> RiskAssessment:
    """Plan -> retrieve -> decide -> verify.

    - chunks = gather_context(plan_queries(profile, flags), store, embedder)
    - user content: the profile as JSON (profile.model_dump_json(indent=2)) inside <profile> tags,
      the flags inside <screening_flags> tags (one per line), and the chunks inside <documents> as
      <document id="{chunk.provision_id}">{chunk.text}</document>
    - assessment = complete_structured(provider, [user message], RiskAssessment, system=get_prompt("classifier").system)
    - Verify, in code:
      a) keep only citations whose id is a provision_id of the retrieved chunks; if any were dropped,
         add the flag "dropped_unsupported_citations"
      b) assessment.flags = sorted(set(assessment.flags) | set(flags) | the flags you added)
      c) if an "annex_iii:*" flag exists but the category is "minimal_risk" or "limited_risk",
         or "prohibited:*" flag exists but the category isn't "prohibited":
         set confidence = "low" and add flag "rules_disagree_with_llm"
      d) if profile.missing_info is non-empty and confidence is "high", lower it to "medium"
      e) copy the role from the profile when the assessment's role is "unknown"
    """
    chunks = gather_context(plan_queries(profile, flags), store, embedder)
    profile_json = profile.model_dump_json(indent=2)
    user_content = (
        f"<profile>\n{profile_json}\n</profile>\n"
        f"<screening_flags>\n" + "\n".join(flags) + "\n</screening_flags>\n"
        "<documents>\n"
        + "\n".join(f'<document id="{c.provision_id}">{c.text}</document>' for c in chunks)
        + "\n</documents>"
    )
    assessment = complete_structured(
        provider,
        [{"role": "user", "content": user_content}],
        RiskAssessment,
        system=get_prompt("classifier").system,
    )
    added: set[str] = set()

    # a) drop citations that don't match a retrieved document
    n_citations_before = len(assessment.citations)
    valid_ids = {c.provision_id for c in chunks}
    assessment.citations = [c for c in assessment.citations if c in valid_ids]
    if len(assessment.citations) < n_citations_before:
        added.add("dropped_unsupported_citations")

    # c) does the LLM contradict the deterministic rules?
    annex = any(f.startswith("annex_iii:") for f in flags)
    prohibited = any(f.startswith("prohibited:") for f in flags)
    if (annex and assessment.category in ("minimal_risk", "limited_risk")) or (
        prohibited and assessment.category != "prohibited"
    ):
        assessment.confidence = "low"
        added.add("rules_disagree_with_llm")

    # b) merge all flags once: LLM's + rules' + ours, sorted and de-duplicated
    assessment.flags = sorted(set(assessment.flags) | set(flags) | added)

    # d) missing facts → no high confidence
    if profile.missing_info and assessment.confidence == "high":
        assessment.confidence = "medium"

    # e) fill in the role from the intake profile
    if assessment.role == "unknown":
        assessment.role = profile.role

    return assessment
