"""Crawler data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CrawledResource:
    url: str
    resource_type: str
    mime_type: str | None = None
    size_bytes: int | None = None
    status_code: int | None = None
    is_external: bool = False
    domain: str | None = None
    load_time: float | None = None
    # Inline script content retained ONLY for small inline <script> blocks,
    # used by the technology detector. Never persisted wholesale.
    inline_content: str | None = None


@dataclass
class CrawledPage:
    url: str
    status_code: int | None = None
    content_type: str | None = None
    final_url: str = ""
    depth: int = 0
    title: str | None = None
    meta_description: str | None = None
    canonical_url: str | None = None
    word_count: int | None = None
    html_size: int | None = None
    load_time: float | None = None
    html: str = ""
    text: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    cookies: list[dict[str, Any]] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    resources: list[CrawledResource] = field(default_factory=list)
    robots_blocked: bool = False


@dataclass
class CrawlResult:
    base_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    robots_disallowed: bool = False
    error: str | None = None

    @property
    def all_resources(self) -> list[CrawledResource]:
        return [r for p in self.pages for r in p.resources]
