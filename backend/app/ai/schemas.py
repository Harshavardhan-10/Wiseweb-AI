"""Pydantic schemas for validated AI outputs.

Every AI response is validated against these before persistence. If the
AI returns invalid JSON or fails validation, the pipeline falls back to
deterministic generation rather than storing garbage.
"""

from pydantic import BaseModel, Field


class RootCause(BaseModel):
    title: str
    description: str = ""
    affected_findings: list[str] = Field(default_factory=list)  # rule_ids or finding titles
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)


class RootCauseOutput(BaseModel):
    root_causes: list[RootCause] = Field(default_factory=list)


class Recommendation(BaseModel):
    title: str
    description: str = ""
    category: str = "PERFORMANCE"
    priority: str = "P2"
    impact: str = "MEDIUM"
    effort: str = "MEDIUM"
    confidence: float = Field(default=0.5, ge=0, le=1)
    root_cause: str = ""
    finding_ids: list[int] = Field(default_factory=list)
    implementation_guidance: str = ""


class RecommendationOutput(BaseModel):
    recommendations: list[Recommendation] = Field(default_factory=list)


class SummaryItem(BaseModel):
    headline: str = ""
    executive_summary: str = ""
    top_risks: list[str] = Field(default_factory=list)
    biggest_opportunities: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)


class CompetitorGap(BaseModel):
    dimension: str
    you: float | None = None
    competitor: float | None = None
    gap: float | None = None
    explanation: str = ""


class CompetitorOutput(BaseModel):
    gaps: list[CompetitorGap] = Field(default_factory=list)
    explanation: str = ""
    summary: str = ""
