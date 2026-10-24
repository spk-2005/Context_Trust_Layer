import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Folder(Base):
    __tablename__ = "folders"

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_folders_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "parent_id"],
            ["folders.organization_id", "folders.id"],
            name="fk_folders_parent_same_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("depth >= 0 AND depth <= 6", name="chk_folders_depth"),
        Index("idx_folders_org_parent", "organization_id", "parent_id"),
        Index("idx_folders_org_depth", "organization_id", "depth"),
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
            name="fk_folders_organization",
        ),
        nullable=False,
    )

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    depth: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("FALSE"),
    )

    folder_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        server_default=text("'general'"),
    )

    icon: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    color: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_folders_creator",
        ),
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
    children: Mapped[List["Folder"]] = relationship(
        "Folder",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    parent: Mapped[Optional["Folder"]] = relationship(
        "Folder",
        back_populates="children",
        remote_side=[organization_id, id],
    )

    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="folder",
        overlaps="organization,documents",
    )
