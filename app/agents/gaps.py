"""PHASE 5 · Gap analysis: what's already in place vs what's required (deterministic)."""

from __future__ import annotations

from datetime import date

from app.agents.schemas import Gap, Obligation

ORDER = {"high": 0, "medium": 1, "low": 2}


def find_gaps(
    obligations: list[Obligation], practices: dict[str, str], today: date | None = None
) -> list[Gap]:
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
    if today is None:
        today = date.today()
    gaps = []
    for ob in obligations:
        status = practices.get(ob.id, "unknown").lower()
        if status == "yes":
            status = "in_place"
        elif status == "partial":
            status = "partial"
        elif status == "no":
            status = "missing"
        else:
            status = "unknown"
        applies_from = date.fromisoformat(ob.applies_from)
        if status == "in_place":
            priority = "low"
        elif applies_from <= today and status in ("missing", "unknown"):
            priority = "high"
        elif (applies_from - today).days <= 365 and status == "missing":
            priority = "high"
        else:
            priority = "medium"
        gaps.append(
            Gap(
                obligation_id=ob.id,
                title=ob.title,
                status=status,
                priority=priority,
                applies_from=ob.applies_from,
            )
        )

    return sorted(gaps, key=lambda g: (ORDER[g.priority], g.applies_from, g.obligation_id))
