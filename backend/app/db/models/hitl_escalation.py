import uuid
from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HitlEscalation(Base):
    __tablename__ = "hitl_escalations"

    __table_args__ = (
        Index("idx_hitl_org", "organization_id"),
        Index("idx_hitl_status", "organization_id", "status"),
        Index("idx_hitl_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    audit_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    actor_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    actor_role: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    action_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    reasons: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Operational Triage",
    )

    liability_prevented_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",  # "PENDING" | "APPROVED" | "REJECTED"
    )

    suggested_action: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    resolved_by_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    resolved_by_role: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    resolution_decision: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,  # "APPROVE" | "REJECT"
    )

    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
