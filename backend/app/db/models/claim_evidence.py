import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    __table_args__ = (
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="chk_page_number",
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
            name="fk_claim_evidence_claim",
        ),
        nullable=False,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "documents.id",
            ondelete="CASCADE",
            name="fk_claim_evidence_document",
        ),
        nullable=False,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    section: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    text_span: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    start_offset: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    end_offset: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    evidence_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    claim = relationship(
        "Claim",
        back_populates="evidence",
    )

    document = relationship(
        "Document",
        back_populates="evidence_records",
    )
