from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScoreDelta(BaseModel):
    label: str
    before: float | None
    after: float | None
    delta: float | None


class ChangeItem(BaseModel):
    type: str  # added | removed | changed
    category: str
    label: str
    detail: str | None = None


class ScanComparisonCreate(BaseModel):
    base_scan_id: int
    compare_scan_id: int


class ScanComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_id: int
    base_scan_id: int
    compare_scan_id: int
    changes: dict | None
    summary: str | None
    created_at: datetime
