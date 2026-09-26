"""PHASE 5 · Obligations agent: classification -> the obligations that apply (deterministic).

Obligations come from a curated table (data/obligations.yaml) instead of the LLM: when the
answer must be exact and auditable, look it up; don't generate it.
"""

from __future__ import annotations

import os
from functools import lru_cache

import yaml

from app.agents.schemas import Obligation, RiskAssessment

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "obligations.yaml")


@lru_cache
def load_table(path: str = DATA) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def lookup(assessment: RiskAssessment, table: list[dict] | None = None) -> list[Obligation]:
    """Select the obligations for this assessment, in table order.

    An entry applies when BOTH:
    - its "categories" contain assessment.category, OR it contains "transparency" and
      assessment.transparency_obligations is True
    - its "applies_to" is "all", or equals assessment.role, or assessment.role is "both" or "unknown"
      (when the role is unclear we show both sides rather than hide duties)
    Build Obligation objects from the entries (ignore the "categories" key).
    """
    # YOUR CODE
    raise NotImplementedError
