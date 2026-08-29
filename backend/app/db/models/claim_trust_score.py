import decimal
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClaimTrustScore(Base):
    __tablename__ = "claim_trust_scores"

    __table_args__ = (
        CheckConstraint(
            "source_score BETWEEN 0 AND 1",
            name="chk_source_score",
        ),
        CheckConstraint(
            "freshness_score BETWEEN 0 AND 1",
            name="chk_freshness_score",
        ),
        CheckConstraint(
            "evidence_score BETWEEN 0 AND 1",
            name="chk_evidence_score",
        ),
        CheckConstraint(
            "consistency_score BETWEEN 0 AND 1",
            name="chk_consistency_score",
        ),
        CheckConstraint(
            "authority_score BETWEEN 0 AND 1",
            name="chk_authority_score",
        ),
        CheckConstraint(
            "human_score BETWEEN 0 AND 1",
            name="chk_human_score",
        ),
        CheckConstraint(
            "overall_score BETWEEN 0 AND 1",
            name="chk_overall_score",
        ),
        Index(
            "idx_claim_trust_claim",
            "claim_id",
        ),
        Index(
            "idx_claim_trust_overall",
            text("overall_score DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claims.id",
            ondelete="CASCADE",
            name="fk_trust_scores_claim",
        ),
        nullable=False,
    )

    source_score: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    freshness_score: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    evidence_score: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    consistency_score: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    authority_score: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    human_score: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=decimal.Decimal("0.0000"),
        server_default=text("0.0000"),
    )

    overall_score: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    scoring_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    scoring_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    claim = relationship(
        "Claim",
        back_populates="trust_scores",
    )
