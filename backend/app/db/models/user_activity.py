import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"

    __table_args__ = (
        Index(
            "idx_activity_organization",
            "organization_id",
        ),
        Index(
            "idx_activity_user",
            "user_id",
        ),
        Index(
            "idx_activity_created_at",
            "created_at",
        ),
        Index(
            "idx_activity_action_type",
            "action_type",
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
            name="fk_activity_organization",
        ),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_activity_user",
        ),
        nullable=True,
    )

    user_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="System",
        server_default=text("'System'"),
    )

    user_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="system",
        server_default=text("'system'"),
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    target_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    target_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    target_title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="General",
        server_default=text("'General'"),
    )

    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="activities",
    )

    user = relationship(
        "User",
        back_populates="activities",
    )
