from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.website import WEBSITE_TYPES


class WebsiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=3, max_length=2048)
    website_type: str = Field(default="other", pattern="|".join(WEBSITE_TYPES))
    industry: str | None = Field(default=None, max_length=128)
    target_audience: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1024)

    @field_validator("url")
    @classmethod
    def url_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL must not be blank")
        return v


class WebsiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=3, max_length=2048)
    website_type: str | None = Field(default=None, pattern="|".join(WEBSITE_TYPES))
    industry: str | None = Field(default=None, max_length=128)
    target_audience: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1024)


class WebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    url: str
    normalized_url: str
    website_type: str
    industry: str | None
    target_audience: str | None
    description: str | None
    monitoring_enabled: bool
    last_scanned_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=3, max_length=2048)


class CompetitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_id: int
    name: str
    url: str
    normalized_url: str
    created_at: datetime
