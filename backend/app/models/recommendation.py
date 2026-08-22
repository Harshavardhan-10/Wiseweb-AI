from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

PRIORITIES = ("P0", "P1", "P2", "P3")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(4), default="P2", index=True, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    impact: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)
    effort: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    finding_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="recommendations")
