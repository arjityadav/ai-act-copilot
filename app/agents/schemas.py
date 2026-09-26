"""Data contracts between agents (given). Every agent reads and writes these Pydantic models,
so each step is validated and the whole pipeline is inspectable and testable."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AnnexIIIArea = Literal["none", "biometrics", "critical_infrastructure", "education", "employment",
                       "essential_services", "law_enforcement", "migration", "justice_democracy", "unknown"]
Category = Literal["prohibited", "high_risk", "limited_risk", "minimal_risk", "gpai"]
Role = Literal["provider", "deployer", "both", "unknown"]


class SystemProfile(BaseModel):
    """What the intake agent extracts from the user's free-text description."""
    name: str = Field(description="Short name of the AI system")
    purpose: str = Field(description="What the system does, in one or two sentences")
    sector: str = Field(description="Where it is used, e.g. HR, banking, education, retail, public sector")
    role: Role = Field(description="provider = develops/sells it under own name; deployer = uses it professionally")
    affected_persons: str = Field(description="Whose lives the outputs affect")
    decisions_about_people: bool = Field(description="Outputs are used to make or support decisions about individuals")
    uses_biometrics: bool = Field(description="Processes faces, voices, fingerprints or other biometric data")
    emotion_recognition: bool = Field(description="Infers emotions or intentions from biometric data")
    interacts_with_people: bool = Field(description="Talks to people directly, e.g. chatbot or voice agent")
    generates_content: bool = Field(description="Generates or manipulates images, audio, video or text")
    is_general_purpose_model: bool = Field(description="Is itself a general-purpose AI model offered to others")
    safety_component_of_product: bool = Field(description="Safety component of a regulated product (machinery, medical device, vehicle, toy...)")
    annex_iii_area: AnnexIIIArea = Field(description="Best-matching Annex III area, 'none' if clearly none, 'unknown' if unclear")
    missing_info: list[str] = Field(default_factory=list, description="Questions to ask the user if key facts are missing")


class RiskAssessment(BaseModel):
    category: Category
    annex_iii_area: AnnexIIIArea = "none"
    role: Role = "unknown"
    transparency_obligations: bool = Field(default=False, description="Article 50 applies (in addition to the category)")
    reasoning: str = Field(description="Step-by-step reasoning referring to the cited provisions")
    citations: list[str] = Field(default_factory=list, description="Provision ids relied on, e.g. 'art-5', 'art-6', 'annex-iii'")
    confidence: Literal["low", "medium", "high"] = "medium"
    flags: list[str] = Field(default_factory=list)


class Obligation(BaseModel):
    id: str
    title: str
    articles: list[str]
    applies_to: Literal["provider", "deployer", "all"]
    applies_from: str
    description: str


class Gap(BaseModel):
    obligation_id: str
    title: str
    status: Literal["in_place", "partial", "missing", "unknown"]
    priority: Literal["high", "medium", "low"]
    applies_from: str


class Report(BaseModel):
    markdown: str
    cited_provisions: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
