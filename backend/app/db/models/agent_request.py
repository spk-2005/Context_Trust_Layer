import decimal
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentRequest(Base):
    __tablename__ = "agent_requests"

    __table_args__ = (
        CheckConstraint(
            "trust_threshold BETWEEN 0 AND 1",
            name="chk_trust_threshold",
        ),
        CheckConstraint(
            "max_results > 0",
            name="chk_max_results",
        ),
        Index(
            "idx_agent_requests_organization",
            "organization_id",
        ),
        Index(
            "idx_agent_requests_agent",
            "agent_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
            name="fk_agent_requests_organization",
        ),
        nullable=False,
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "agents.id",
            ondelete="CASCADE",
            name="fk_agent_requests_agent",
        ),
        nullable=False,
    )

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    trust_threshold: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=decimal.Decimal("0.8000"),
        server_default=text("0.8000"),
    )

    max_results: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default=text("10"),
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="agent_requests",
    )

    agent = relationship(
        "Agent",
        back_populates="requests",
    )

    context_items = relationship(
        "AgentContextItem",
        back_populates="request",
        cascade="all, delete-orphan",
    )
