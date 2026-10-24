import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, JSON, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import OrganizationStatus


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(
            OrganizationStatus,
            name="organization_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
        server_default=text("'active'"),
    )

    domain_whitelist: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )

    allowed_auth_methods: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: ["password", "google", "microsoft", "okta"],
    )

    governance_config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    setup_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
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
    invites = relationship(
        "OrganizationInvite",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    users = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    data_sources = relationship(
        "DataSource",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    documents = relationship(
        "Document",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    claims = relationship(
        "Claim",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    agents = relationship(
        "Agent",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    agent_requests = relationship(
        "AgentRequest",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    human_reviews = relationship(
        "HumanReview",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    activities = relationship(
        "UserActivityLog",
        back_populates="organization",
        cascade="all, delete-orphan",
    )