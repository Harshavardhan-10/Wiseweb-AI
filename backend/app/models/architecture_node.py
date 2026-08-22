from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.core.database import Base

NODE_TYPES = ("PAGE", "TECHNOLOGY", "API", "THIRD_PARTY", "RESOURCE", "DOMAIN", "SERVICE")


class ArchitectureNode(Base):
    __tablename__ = "architecture_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    label: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    scan = orm_relationship("Scan", back_populates="architecture_nodes")
    outgoing_edges = orm_relationship(
        "ArchitectureEdge",
        foreign_keys="ArchitectureEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )


class ArchitectureEdge(Base):
    __tablename__ = "architecture_edges"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_node_id: Mapped[int] = mapped_column(
        ForeignKey("architecture_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[int] = mapped_column(
        ForeignKey("architecture_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    scan = orm_relationship("Scan", back_populates="architecture_edges")
    source_node = orm_relationship(
        "ArchitectureNode", foreign_keys=[source_node_id], back_populates="outgoing_edges"
    )
