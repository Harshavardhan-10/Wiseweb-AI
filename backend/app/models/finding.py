from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

FINDING_CATEGORIES = ("SECURITY", "PERFORMANCE", "ACCESSIBILITY", "PRIVACY",
                      "SEO", "CONTENT", "UX", "ARCHITECTURE")
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
FINDING_STATUSES = ("OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "FIXED", "VERIFIED", "DISMISSED")
IMPACT_LEVELS = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
EFFORT_LEVELS = ("HIGH", "MEDIUM", "LOW")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="INFO", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    impact: Mapped[str] = mapped_column(String(16), default="LOW", nullable=False)
    effort: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)
    affected_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="findings")
    evidence = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")
