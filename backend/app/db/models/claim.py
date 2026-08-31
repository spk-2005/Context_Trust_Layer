import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ClaimStatus


class Claim(Base):
    __tablename__ = "claims"

    __table_args__ = (
        Index(
            "idx_claims_organization",
            "organization_id",
        ),
        Index(
            "idx_claims_document_version",
            "document_version_id",
        ),
        Index(
            "idx_claims_status",
            "status",
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
            name="fk_claims_organization",
        ),
        nullable=False,
    )

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_versions.id",
            ondelete="CASCADE",
            name="fk_claims_document_version",
        ),
        nullable=False,
    )

    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    predicate: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    object: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    claim_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    extraction_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    extraction_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[ClaimStatus] = mapped_column(
        Enum(
            ClaimStatus,
            name="claim_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ClaimStatus.CANDIDATE,
        server_default=text("'candidate'"),
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
        back_populates="claims",
    )

    document_version = relationship(
        "DocumentVersion",
        back_populates="claims",
    )

    evidence = relationship(
        "ClaimEvidence",
        back_populates="claim",
        cascade="all, delete-orphan",
    )

    validity_records = relationship(
        "ClaimValidity",
        back_populates="claim",
        cascade="all, delete-orphan",
    )

    trust_scores = relationship(
        "ClaimTrustScore",
        back_populates="claim",
        cascade="all, delete-orphan",
    )

    conflicts_as_a = relationship(
        "ClaimConflict",
        foreign_keys="ClaimConflict.claim_a_id",
        back_populates="claim_a",
        cascade="all, delete-orphan",
    )

    conflicts_as_b = relationship(
        "ClaimConflict",
        foreign_keys="ClaimConflict.claim_b_id",
        back_populates="claim_b",
        cascade="all, delete-orphan",
    )

    conflicts_resolved = relationship(
        "ClaimConflict",
        foreign_keys="ClaimConflict.resolved_claim_id",
        back_populates="resolved_claim",
    )

    agent_context_items = relationship(
        "AgentContextItem",
        back_populates="claim",
        cascade="all, delete-orphan",
    )