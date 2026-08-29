import decimal
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentContextItem(Base):
    __tablename__ = "agent_context_items"

    __table_args__ = (
        CheckConstraint(
            "rank > 0",
            name="chk_context_rank",
        ),
        CheckConstraint(
            "trust_score IS NULL OR (trust_score BETWEEN 0 AND 1)",
            name="chk_context_trust_score",
        ),
        UniqueConstraint(
            "request_id",
            "claim_id",
            name="uq_request_claim",
        ),
        Index(
            "idx_context_items_request",
            "request_id",
        ),
        Index(
            "idx_context_items_claim",
            "claim_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "agent_requests.id",
            ondelete="CASCADE",
            name="fk_context_request",
        ),
        nullable=False,
    )

    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claims.id",
            ondelete="CASCADE",
            name="fk_context_claim",
        ),
        nullable=False,
    )

    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    trust_score: Mapped[decimal.Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    included: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("TRUE"),
    )

    exclusion_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    request = relationship(
        "AgentRequest",
        back_populates="context_items",
    )

    claim = relationship(
        "Claim",
        back_populates="agent_context_items",
    )
