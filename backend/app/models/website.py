from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

WEBSITE_TYPES = ("portfolio", "ecommerce", "blog", "saas", "corporate",
                 "education", "news", "community", "other")


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), index=True, nullable=False)
    website_type: Mapped[str] = mapped_column(String(32), default="other", nullable=False)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="websites")
    scans = relationship(
        "Scan", back_populates="website", cascade="all, delete-orphan",
        order_by="desc(Scan.started_at)",
    )
    competitors = relationship("Competitor", back_populates="website", cascade="all, delete-orphan")

    @property
    def host(self) -> str:
        from urllib.parse import urlparse
        return urlparse(self.url).netloc
