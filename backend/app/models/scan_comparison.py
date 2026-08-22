from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScanComparison(Base):
    __tablename__ = "scan_comparisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE"), index=True, nullable=False
    )
    base_scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    compare_scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # {added: [...], removed: [...], changed: [...], score_deltas: {...}}
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    website = relationship("Website")
    base_scan = relationship("Scan", foreign_keys=[base_scan_id])
    compare_scan = relationship("Scan", foreign_keys=[compare_scan_id])


class ScanSummary(Base):
    __tablename__ = "scan_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    top_risks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    biggest_opportunities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    roadmap: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="summary")
