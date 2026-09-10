import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DecisionEvaluation(Base):
    __tablename__ = "decision_evaluations"

    __table_args__ = (
        Index("idx_decision_evaluations_org", "organization_id"),
        Index("idx_decision_evaluations_audit_id", "audit_id"),
        Index("idx_decision_evaluations_verdict", "verdict"),
        Index("idx_decision_evaluations_created_at", "created_at"),
        Index("idx_decision_evaluations_actor", "actor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    audit_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
            name="fk_decision_evaluations_org",
        ),
        nullable=False,
    )

    actor_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    actor_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="support",
    )

    decision_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    verdict: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ALLOW",
    )

    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="LOW",
    )

    reasons: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
    )

    preferred_source: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    suggested_action: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    context_items: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
    )

    audit_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    execution_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    organization = relationship(
        "Organization",
        backref="decision_evaluations",
    )
