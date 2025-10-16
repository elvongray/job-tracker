from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import SchemaBase

if TYPE_CHECKING:
    from src.activities.models import Activity
    from src.applications.models import Application
    from src.user.models import User


class ReminderChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    CALENDAR = "calendar"


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


reminder_channel_enum = PgEnum(
    ReminderChannel,
    name="reminder_channel",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
    values_callable=enum_values,
)


class Reminder(SchemaBase):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=True,
    )
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channels: Mapped[list[ReminderChannel]] = mapped_column(
        ARRAY(reminder_channel_enum),
        default=lambda: [ReminderChannel.IN_APP],
        nullable=False,
    )
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(
        BigInteger,
        default=1,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="reminders")
    application: Mapped[Application] = relationship(back_populates="reminders")
    activity: Mapped[Activity] = relationship(back_populates="reminders")

    __table_args__ = (
        CheckConstraint(
            "(application_id IS NOT NULL) OR (activity_id IS NOT NULL)",
            name="ck_reminders_application_or_activity",
        ),
        UniqueConstraint(
            "user_id",
            "dedupe_key",
            name="uq_reminders_user_dedupe_key",
        ),
        Index(
            "ix_reminders_user_id_due_at_pending",
            "user_id",
            "due_at",
            postgresql_where=text("sent = false"),
        ),
    )
