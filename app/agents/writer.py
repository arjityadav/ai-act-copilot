"""Report writer agent (given): turns the structured results into a readable Markdown report."""

from __future__ import annotations

import json
import re

from app.agents.schemas import Gap, Obligation, Report, RiskAssessment, SystemProfile
from app.llmops.prompts import get_prompt

CITE_RE = re.compile(r"\b(Article|Art\.)\s+(\d+[a-z]?)|\bAnnex\s+([IVXLC]+)\b")


def cited_provisions(markdown: str) -> list[str]:
    """'Article 9', 'Art. 50', 'Annex III' -> ['art-9', 'art-50', 'annex-iii'] (unique, in order)."""
    out = []
    for m in CITE_RE.finditer(markdown):
        pid = f"art-{m.group(2).lower()}" if m.group(2) else f"annex-{m.group(3).lower()}"
        if pid not in out:
            out.append(pid)
    return out


def write_report(profile: SystemProfile, assessment: RiskAssessment, obligations: list[Obligation],
                 gaps: list[Gap], provider, feedback: list[str] | None = None) -> Report:
    payload = {"profile": profile.model_dump(), "classification": assessment.model_dump(),
               "obligations": [o.model_dump() for o in obligations], "gaps": [g.model_dump() for g in gaps]}
    content = "<input>\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n</input>"
    if feedback:
        content += "\n\nA reviewer rejected the previous draft. Fix these issues:\n- " + "\n- ".join(feedback)
    result = provider.complete([{"role": "user", "content": content}], system=get_prompt("writer").system,
                               temperature=0.2, max_tokens=2500)
    return Report(markdown=result.text, cited_provisions=cited_provisions(result.text))
