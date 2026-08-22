from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.scan import SCAN_STAGES, SCAN_STATUSES


class ScanCreate(BaseModel):
    crawl_depth: int = Field(default=3, ge=1, le=5)
    page_limit: int = Field(default=50, ge=1, le=200)

    @model_validator(mode="after")
    def check(self) -> "ScanCreate":
        if self.page_limit < 1 or self.page_limit > 200:
            raise ValueError("page_limit must be between 1 and 200")
        return self


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_id: int
    status: str
    stage: str
    progress_percent: int
    error_message: str | None
    crawl_depth: int
    page_limit: int
    started_at: datetime | None
    completed_at: datetime | None
    pages_discovered: int
    pages_analyzed: int
    overall_score: float | None
    security_score: float | None
    performance_score: float | None
    accessibility_score: float | None
    privacy_score: float | None
    seo_score: float | None
    content_score: float | None
    ux_score: float | None
    architecture_score: float | None
    analyzer_status: dict | None


class ScanListResponse(BaseModel):
    items: list[ScanResponse]
    total: int


class ScanProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_id: int
    status: str
    stage: str
    progress_percent: int
    error_message: str | None
    pages_discovered: int
    pages_analyzed: int
    started_at: datetime | None
    completed_at: datetime | None
