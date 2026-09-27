"""PHASE 5 · Verifier agent: checks the report in code before anyone sees it.

Read first: notes Days 50 (LLM-as-judge), 59 (verifying citations), 67 (evaluator–optimiser pattern).

The writer is an LLM and can hallucinate an article number or skip the disclaimer. The
verifier catches that deterministically; if it fails, the graph sends its issues back to the
writer (evaluator–optimiser loop, at most 2 retries).
"""

from __future__ import annotations

from app.agents.schemas import Obligation, Report, RiskAssessment, VerificationResult

CATEGORY_WORDS = {
    "prohibited": "prohibited",
    "high_risk": "high-risk",
    "limited_risk": "limited",
    "minimal_risk": "minimal",
    "gpai": "general-purpose",
}


def verify_report(
    report: Report, assessment: RiskAssessment, obligations: list[Obligation], known_provisions: set[str]
) -> VerificationResult:
    """Collect human-readable issues (strings); passed = no issues.

    1. Every id in report.cited_provisions must be in known_provisions (the ingested corpus's
       provision ids, e.g. {"art-5", "art-6", "annex-iii", ...}).
       Issue: f"Cites {pid}, which is not in the regulation text"
    2. The report (lower-cased) must mention the category word from CATEGORY_WORDS.
       Issue: f"Does not state the classification ({word})"
    3. Every obligation's applies_from date must appear in the report text.
       Issue: f"Missing deadline {ob.applies_from} for '{ob.title}'"
    4. The report must contain the word "disclaimer" and the phrase "not legal advice" (case-insensitive).
       Issue: "Missing disclaimer"
    """
    issues: list[str] = []
    for pid in report.cited_provisions:
        if pid not in known_provisions:
            issues.append(f"Cites {pid}, which is not in the regulation text")
    word = CATEGORY_WORDS[assessment.category]
    report_markdown = report.markdown.lower()
    if word not in report_markdown:
        issues.append(f"Does not state the classification ({word})")
    s = report_markdown
    for ob in obligations:
        if ob.applies_from not in s:
            issues.append(f"Missing deadline {ob.applies_from} for '{ob.title}'")
    if "disclaimer" not in s or "not legal advice" not in s:
        issues.append("Missing disclaimer")
    return VerificationResult(passed=not issues, issues=issues)
