import decimal
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ReviewDecision


class HumanReview(Base):
    __tablename__ = "human_reviews"

    __table_args__ = (
        CheckConstraint(
            "previous_score IS NULL OR (previous_score BETWEEN 0 AND 1)",
            name="chk_previous_score",
        ),
        CheckConstraint(
            "new_score IS NULL OR (new_score BETWEEN 0 AND 1)",
            name="chk_new_score",
        ),
        Index(
            "idx_human_reviews_organization",
            "organization_id",
        ),
        Index(
            "idx_human_reviews_target",
            "target_type",
            "target_id",
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
            name="fk_human_reviews_organization",
        ),
        nullable=False,
    )

    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_human_reviews_reviewer",
        ),
        nullable=False,
    )

    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(
            ReviewDecision,
            name="review_decision",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    previous_score: Mapped[decimal.Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    new_score: Mapped[decimal.Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="human_reviews",
    )

    reviewer = relationship(
        "User",
        back_populates="human_reviews",
    )
