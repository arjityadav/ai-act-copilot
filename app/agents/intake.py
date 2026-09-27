"""PHASE 4 · Intake agent: free text -> validated SystemProfile.

Read first: notes Days 45 (structured output), 71 (context engineering).
"""

from __future__ import annotations

from app.agents.schemas import SystemProfile
from app.llm.structured import complete_structured
from app.llmops.prompts import get_prompt


def extract_profile(description: str, provider, answers: dict[str, str] | None = None) -> SystemProfile:
    """Build a SystemProfile from the user's description (plus answers to earlier clarifying questions).

    - content = "<description>\\n{description}\\n</description>"
      If answers is non-empty, append "\\n<clarifications>\\n" + one line per item "Q: {q}\\nA: {a}" + "\\n</clarifications>"
    - profile = complete_structured(provider, [{"role": "user", "content": content}], SystemProfile,
                                    system=get_prompt("intake").system)
    - If answers were given, the questions they answer are no longer missing: remove from
      profile.missing_info every question that is a key in `answers`.
    - If profile.role == "unknown" and no missing_info item mentions "develop" or "provider",
      append: "Does your organisation develop this system (provider) or use a system built by someone else (deployer)?"
    - Return the profile.
    """
    content = f"<description>\n{description}\n</description>"
    if answers:
        clarifications = "\n".join(f"Q: {q}\nA: {a}" for q, a in answers.items())
        content += f"\n<clarifications>\n{clarifications}\n</clarifications>"

    profile = complete_structured(
        provider,
        [{"role": "user", "content": content}],
        SystemProfile,
        system=get_prompt("intake").system,
    )

    if answers:
        profile.missing_info = [q for q in profile.missing_info if q not in answers]

    if profile.role == "unknown" and not any(
        word in " ".join(profile.missing_info).lower() for word in ("develop", "provider")
    ):
        profile.missing_info.append(
            "Does your organisation develop this system (provider) or use a system built by someone else (deployer)?"
        )

    return profile
