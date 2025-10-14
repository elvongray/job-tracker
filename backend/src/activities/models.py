from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import SchemaBase

if TYPE_CHECKING:
    from src.applications.models import Application
    from src.reminders.models import Reminder
    from src.user.models import User


class ActivityType(str, Enum):
    INTERVIEW = "Interview"
    FOLLOW_UP = "FollowUp"
    CALL = "Call"
    EMAIL = "Email"
    OTHER = "Other"


class ActivityStatus(str, Enum):
    SCHEDULED = "scheduled"
    DONE = "done"
    CANCELED = "canceled"


class InterviewStage(str, Enum):
    SCREENING = "screening"
    TECHNICAL = "technical"
    LOOP = "loop"
    OFFER = "offer"
    OTHER = "other"


class InterviewMedium(str, Enum):
    ONSITE = "onsite"
    ZOOM = "zoom"
    PHONE = "phone"
    GOOGLE_MEET = "google_meet"
    TEAMS = "teams"
    OTHER = "other"


class FollowupChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"
    OTHER = "other"


activity_type_enum = PgEnum(
    ActivityType,
    name="activity_type",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)

activity_status_enum = PgEnum(
    ActivityStatus,
    name="activity_status",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)

interview_stage_enum = PgEnum(
    InterviewStage,
    name="interview_stage",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)

interview_medium_enum = PgEnum(
    InterviewMedium,
    name="interview_medium",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)

followup_channel_enum = PgEnum(
    FollowupChannel,
    name="followup_channel",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)


class Activity(SchemaBase):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ActivityType] = mapped_column(
        activity_type_enum,
        nullable=False,
    )
    status: Mapped[ActivityStatus] = mapped_column(
        activity_status_enum,
        default=ActivityStatus.SCHEDULED,
        nullable=False,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_action_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_contacts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Interview specific fields
    interview_stage: Mapped[InterviewStage | None] = mapped_column(
        interview_stage_enum,
        nullable=True,
    )
    interview_medium: Mapped[InterviewMedium | None] = mapped_column(
        interview_medium_enum,
        nullable=True,
    )
    location_or_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    agenda: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_checklist: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Follow-up specific fields
    followup_channel: Mapped[FollowupChannel | None] = mapped_column(
        followup_channel_enum,
        nullable=True,
    )
    template_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    version: Mapped[int] = mapped_column(
        BigInteger,
        default=1,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="activities")
    application: Mapped[Application] = relationship(back_populates="activities")
    reminders: Mapped[list[Reminder]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status != 'scheduled' OR starts_at IS NOT NULL",
            name="ck_activities_scheduled_requires_starts_at",
        ),
        Index(
            "ix_activities_user_id_starts_at",
            "user_id",
            "starts_at",
        ),
        Index(
            "ix_activities_user_id_next_action_due",
            "user_id",
            "next_action_due",
        ),
    )
