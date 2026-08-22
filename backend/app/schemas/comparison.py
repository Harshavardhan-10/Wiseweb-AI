from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScoreEntry(BaseModel):
    label: str
    score: float | None
    findings_count: int


class SiteComparison(BaseModel):
    website_id: int | None
    name: str
    url: str
    is_self: bool
    is_demo: bool = False
    scores: dict[str, float | None]
    scan_id: int | None
    scanned_at: datetime | None


class ComparisonCreate(BaseModel):
    website_id: int
    competitor_ids: list[int] = []
    website_ids: list[int] = []


class ComparisonResponse(BaseModel):
    sites: list[SiteComparison]
    ai_explanation: str | None = None
    gaps: dict | None = None
