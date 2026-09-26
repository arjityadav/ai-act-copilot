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
    # YOUR CODE
    raise NotImplementedError


def gather_context(queries: list[str], store, embedder, per_query: int = 4, max_chunks: int = 14) -> list[Chunk]:
    """Run hybrid_search(q, store, embedder, k=per_query) for each query; keep chunks in order of
    first appearance without duplicate ids; stop at max_chunks."""
    # YOUR CODE
    raise NotImplementedError


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
    # YOUR CODE
    raise NotImplementedError

