from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import SchemaBase

if TYPE_CHECKING:
    from src.activities.models import Activity
    from src.applications.models import Application
    from src.auth.models import MagicLinkToken
    from src.reminders.models import Reminder


class User(SchemaBase):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="Africa/Lagos",
        nullable=False,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    session_timeout_mins: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4320
    )
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    settings: Mapped[UserSettings] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list[Activity]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reminders: Mapped[list[Reminder]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    magic_link_tokens: Mapped[list[MagicLinkToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserSettings(SchemaBase):
    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quiet_hours_start: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
    )
    quiet_hours_end: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
    )
    reminder_defaults: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    user: Mapped[User] = relationship(back_populates="settings")
