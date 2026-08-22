from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    title: str
    description: str | None
    priority: str
    priority_score: float
    impact: str
    effort: str
    confidence: float
    category: str
    root_cause: str | None
    implementation_guidance: str | None
    finding_ids: list
    status: str
    created_at: datetime


class RecommendationUpdate(BaseModel):
    status: str


class RecommendationListResponse(BaseModel):
    items: list[RecommendationResponse]
    total: int
