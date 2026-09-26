"""PHASE 4 · Deterministic screening rules.

Read first: notes Day 67 (workflows vs agents), supplement S7 (EU AI Act).

LLMs are good at reading messy descriptions; plain code is good at applying fixed rules the
same way every time. Combining both is a core agent-design pattern: the rules run first, their
flags go into the classifier's prompt, and afterwards we check the LLM didn't contradict them.
"""

from __future__ import annotations

from app.agents.schemas import SystemProfile

WORKPLACE_OR_EDUCATION = ("hr", "human resources", "employment", "workplace", "recruit", "education",
                          "school", "university", "employee")


def screen(profile: SystemProfile) -> list[str]:
    """Return sorted, de-duplicated flags from these rules:

    "prohibited:emotion_recognition_work_education"
        profile.emotion_recognition is True AND profile.sector (lower-cased) contains any WORKPLACE_OR_EDUCATION word
    "annex_iii:<area>"          profile.annex_iii_area is not "none" or "unknown"   (e.g. "annex_iii:employment")
    "annex_i:safety_component"  profile.safety_component_of_product
    "transparency:interaction"  profile.interacts_with_people
    "transparency:synthetic_content"   profile.generates_content
    "gpai:model"                profile.is_general_purpose_model
    "biometrics"                profile.uses_biometrics
    "decisions_about_people"    profile.decisions_about_people
    "role_unknown"              profile.role == "unknown"
    """
    # YOUR CODE
    raise NotImplementedError
