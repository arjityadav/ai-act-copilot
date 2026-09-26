"""PHASE 5 · Gap analysis: what's already in place vs what's required (deterministic)."""

from __future__ import annotations

from datetime import date

from app.agents.schemas import Gap, Obligation


def find_gaps(obligations: list[Obligation], practices: dict[str, str], today: date | None = None) -> list[Gap]:
    """One Gap per obligation, sorted by priority (high, medium, low), then applies_from, then id.

    - status: practices.get(ob.id) normalised to lower case: "yes" -> "in_place", "partial" -> "partial",
      "no" -> "missing"; anything else or absent -> "unknown"
    - priority:
        "low"    if status is "in_place"
        "high"   if the obligation already applies (applies_from <= today) and status is "missing" or "unknown"
        "high"   if it applies within 365 days and status is "missing"
        "medium" otherwise
    - today defaults to date.today(); applies_from is an ISO date string ("2027-12-02")
    """
    # YOUR CODE
    raise NotImplementedError
