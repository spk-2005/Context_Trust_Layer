import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SlackInstallation(Base):
    __tablename__ = "slack_installations"

    __table_args__ = (
        Index("idx_slack_installations_team", "slack_team_id", unique=True),
        Index("idx_slack_installations_org", "organization_id"),
        Index("idx_slack_installations_active", "is_active"),
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

    slack_team_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
    )

    slack_team_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    bot_user_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="",
    )

    encrypted_bot_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    installed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    scopes: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: ["commands", "chat:write"],
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

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class SlackUserIdentity(Base):
    __tablename__ = "slack_user_identities"

    __table_args__ = (
        UniqueConstraint("slack_team_id", "slack_user_id", name="uq_slack_team_user"),
        Index("idx_slack_identities_team_user", "slack_team_id", "slack_user_id"),
        Index("idx_slack_identities_org", "organization_id"),
        Index("idx_slack_identities_trulin_user", "trulin_user_id"),
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

    slack_team_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    slack_user_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    trulin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class SlackInboundRequest(Base):
    __tablename__ = "slack_inbound_requests"

    __table_args__ = (
        Index("idx_slack_requests_fingerprint", "query_fingerprint", unique=True),
        Index("idx_slack_requests_trace", "trace_id"),
        Index("idx_slack_requests_org", "organization_id"),
        Index("idx_slack_requests_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )

    slack_team_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    slack_user_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    slack_channel_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    command: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="/trulin",
    )

    query_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    response_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    response_url_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    trigger_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="QUEUED",  # "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "EXPIRED", "UNLINKED"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    jobs = relationship("SlackJob", back_populates="request", cascade="all, delete-orphan")
    ledger_entries = relationship("SlackDeliveryLedger", back_populates="request", cascade="all, delete-orphan")


class SlackJob(Base):
    __tablename__ = "slack_jobs"

    __table_args__ = (
        Index("idx_slack_jobs_status_next_run", "status", "next_run_at"),
        Index("idx_slack_jobs_request", "inbound_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    inbound_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("slack_inbound_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="QUEUED",  # "QUEUED", "RUNNING", "COMPLETED", "FAILED"
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    locked_by: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    error_message: Mapped[Optional[str]] = mapped_column(
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

    request = relationship("SlackInboundRequest", back_populates="jobs")


class SlackDeliveryLedger(Base):
    __tablename__ = "slack_delivery_ledger"

    __table_args__ = (
        Index("idx_slack_ledger_request", "inbound_request_id"),
        Index("idx_slack_ledger_trace", "trace_id"),
        Index("idx_slack_ledger_status", "delivery_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    inbound_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("slack_inbound_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    delivery_target: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="response_url",  # "response_url" | "chat.postEphemeral"
    )

    delivery_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SUCCESS",  # "SUCCESS", "FAILED", "RETRIED", "EXPIRED"
    )

    http_status: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    request = relationship("SlackInboundRequest", back_populates="ledger_entries")


class SlackFeedback(Base):
    __tablename__ = "slack_feedbacks"

    __table_args__ = (
        Index("idx_slack_feedback_trace", "trace_id"),
        Index("idx_slack_feedback_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    trulin_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    feedback_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # "REPORT_ISSUE", "REQUEST_REVIEW", "UPVOTE", "DOWNVOTE"
    )

    reviewer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
