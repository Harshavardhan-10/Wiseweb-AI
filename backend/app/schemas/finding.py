from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.finding import FINDING_STATUSES


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: int
    evidence_type: str
    source: str | None
    value: str | None
    metadata: dict | None = Field(default=None, validation_alias="meta")
    confidence: float


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    category: str
    rule_id: str
    title: str
    description: str | None
    severity: str
    confidence: float
    impact: str
    effort: str
    status: str
    affected_url: str | None
    created_at: datetime
    evidence: list[EvidenceResponse] = []


class FindingUpdate(BaseModel):
    status: str


class FindingListResponse(BaseModel):
    items: list[FindingResponse]
    total: int
