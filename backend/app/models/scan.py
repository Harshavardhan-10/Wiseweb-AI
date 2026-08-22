from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SCAN_STATUSES = ("QUEUED", "CRAWLING", "ANALYZING", "AI_PROCESSING",
                 "COMPLETED", "FAILED", "CANCELLED")

SCAN_STAGES = (
    "QUEUED", "INITIALIZING", "CRAWLING", "ANALYZING_ARCHITECTURE",
    "ANALYZING_SECURITY", "ANALYZING_PERFORMANCE", "ANALYZING_ACCESSIBILITY",
    "ANALYZING_PRIVACY", "ANALYZING_SEO", "ANALYZING_CONTENT", "ANALYZING_UX",
    "AI_CORRELATION", "AI_RECOMMENDATIONS", "AI_SUMMARY", "FINALIZING",
    "COMPLETED",
)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(48), default="QUEUED", nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    crawl_depth: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    page_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pages_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    overall_score: Mapped[float | None] = mapped_column(nullable=True)
    security_score: Mapped[float | None] = mapped_column(nullable=True)
    performance_score: Mapped[float | None] = mapped_column(nullable=True)
    accessibility_score: Mapped[float | None] = mapped_column(nullable=True)
    privacy_score: Mapped[float | None] = mapped_column(nullable=True)
    seo_score: Mapped[float | None] = mapped_column(nullable=True)
    content_score: Mapped[float | None] = mapped_column(nullable=True)
    ux_score: Mapped[float | None] = mapped_column(nullable=True)
    architecture_score: Mapped[float | None] = mapped_column(nullable=True)

    # Per-analyzer status, e.g. {"SECURITY": "COMPLETED", "ACCESSIBILITY": "FAILED"}
    analyzer_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    website = relationship("Website", back_populates="scans")
    pages = relationship("Page", back_populates="scan", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="scan", cascade="all, delete-orphan")
    technologies = relationship("Technology", back_populates="scan", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="scan", cascade="all, delete-orphan")
    architecture_nodes = relationship("ArchitectureNode", back_populates="scan", cascade="all, delete-orphan")
    architecture_edges = relationship("ArchitectureEdge", back_populates="scan", cascade="all, delete-orphan")
    summary = relationship("ScanSummary", back_populates="scan", cascade="all, delete-orphan", uselist=False)
