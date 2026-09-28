"""PHASE 4 · Deterministic screening rules.

Read first: notes Day 67 (workflows vs agents), supplement S7 (EU AI Act).

LLMs are good at reading messy descriptions; plain code is good at applying fixed rules the
same way every time. Combining both is a core agent-design pattern: the rules run first, their
flags go into the classifier's prompt, and afterwards we check the LLM didn't contradict them.
"""

from __future__ import annotations

import re

from app.agents.schemas import SystemProfile

WORKPLACE_OR_EDUCATION = (
    "hr",
    "human resources",
    "employment",
    "workplace",
    "recruit",
    "education",
    "school",
    "university",
    "employee",
    "worker",
    "staff",
    "call centre",
    "call center",
    "student",
    "pupil",
    "teacher",
    "classroom",
)
# Whole words only (optional plural "s"/"es"/"ing"...), so "hr" doesn't match "through" or "three".
WORKPLACE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in WORKPLACE_OR_EDUCATION) + r")\w*\b")


def _workplace_or_education(profile: SystemProfile) -> bool:
    """Look at sector, purpose and affected persons: a call-centre tool that monitors 'agents' may have
    sector 'customer service' while the purpose or affected persons reveal a workplace setting."""
    text = " ".join([profile.sector, profile.purpose, profile.affected_persons]).lower()
    return bool(WORKPLACE_RE.search(text))


def screen(profile: SystemProfile) -> list[str]:
    """Return sorted, de-duplicated flags from these rules:

    "prohibited:emotion_recognition_work_education"
        profile.emotion_recognition is True AND sector, purpose or affected persons mention a
        WORKPLACE_OR_EDUCATION word (whole word)                              (Article 5(1)(f))
    "prohibited:social_scoring"            profile.social_scoring            (Article 5(1)(c))
    "prohibited:untargeted_face_scraping"  profile.untargeted_face_scraping  (Article 5(1)(e))
    "annex_iii:<area>"          profile.annex_iii_area is not "none" or "unknown"   (e.g. "annex_iii:employment")
    "annex_i:safety_component"  profile.safety_component_of_product
    "transparency:interaction"  profile.interacts_with_people
    "transparency:synthetic_content"   profile.generates_content
    "gpai:model"                profile.is_general_purpose_model
    "biometrics"                profile.uses_biometrics
    "decisions_about_people"    profile.decisions_about_people
    "role_unknown"              profile.role == "unknown"
    """
    flags = set()

    if profile.emotion_recognition and _workplace_or_education(profile):
        flags.add("prohibited:emotion_recognition_work_education")

    if profile.social_scoring:
        flags.add("prohibited:social_scoring")

    if profile.untargeted_face_scraping:
        flags.add("prohibited:untargeted_face_scraping")

    if profile.annex_iii_area not in ("none", "unknown"):
        flags.add(f"annex_iii:{profile.annex_iii_area}")

    if profile.safety_component_of_product:
        flags.add("annex_i:safety_component")

    if profile.interacts_with_people:
        flags.add("transparency:interaction")

    if profile.generates_content:
        flags.add("transparency:synthetic_content")

    if profile.is_general_purpose_model:
        flags.add("gpai:model")

    if profile.uses_biometrics:
        flags.add("biometrics")

    if profile.decisions_about_people:
        flags.add("decisions_about_people")

    if profile.role == "unknown":
        flags.add("role_unknown")

    return sorted(flags)
