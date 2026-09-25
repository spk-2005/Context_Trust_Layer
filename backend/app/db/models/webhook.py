import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    __table_args__ = (
        Index("idx_webhooks_organization", "organization_id"),
        Index("idx_webhooks_active", "organization_id", "is_active"),
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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    channel_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="slack",  # "slack" | "pagerduty" | "teams" | "generic"
    )

    min_liability_threshold_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5000.0,
    )

    trigger_on_block: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    trigger_on_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    secret_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
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
    dispatch_logs = relationship(
        "WebhookDispatchLog",
        back_populates="webhook",
        cascade="all, delete-orphan",
    )


class WebhookDispatchLog(Base):
    __tablename__ = "webhook_dispatch_logs"

    __table_args__ = (
        Index("idx_dispatch_webhook", "webhook_id"),
        Index("idx_dispatch_org", "organization_id"),
        Index("idx_dispatch_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # "incident.blocked" | "incident.review" | "test.ping"
    )

    liability_prevented_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    actor_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="system",
    )

    verdict: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    response_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    response_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    webhook = relationship(
        "WebhookSubscription",
        back_populates="dispatch_logs",
    )
