from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import SchemaBase

if TYPE_CHECKING:
    from src.activities.models import Activity
    from src.reminders.models import Reminder
    from src.user.models import User


class AppStatus(str, Enum):
    DRAFT = "Draft"
    APPLIED = "Applied"
    SCREENING = "Screening"
    RECRUITER_CALL = "Recruiter_Call"
    TECH_SCREEN = "Tech_Screen"
    INTERVIEW_LOOP = "Interview_Loop"
    OFFER = "Offer"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    REJECTED = "Rejected"
    ON_HOLD = "On_Hold"


class PriorityLevel(str, Enum):
    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class LocationMode(str, Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"


app_status_enum = PgEnum(
    AppStatus,
    name="app_status",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)

priority_enum = PgEnum(
    PriorityLevel,
    name="priority_level",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)

location_mode_enum = PgEnum(
    LocationMode,
    name="location_mode",
    metadata=SchemaBase.metadata,
    create_type=True,
    validate_strings=True,
)


class Application(SchemaBase):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[AppStatus] = mapped_column(
        app_status_enum,
        default=AppStatus.APPLIED,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(128),
        default="Other",
        nullable=False,
    )
    application_date: Mapped[date] = mapped_column(
        Date,
        default=lambda: datetime.now(timezone.utc).date(),
        nullable=False,
    )
    priority: Mapped[PriorityLevel] = mapped_column(
        priority_enum,
        default=PriorityLevel.NONE,
        nullable=False,
    )
    location_mode: Mapped[LocationMode] = mapped_column(
        location_mode_enum,
        default=LocationMode.REMOTE,
        nullable=False,
    )
    location_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    timezone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    job_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    salary_min: Mapped[Numeric | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    salary_max: Mapped[Numeric | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    salary_currency: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
    )
    job_requisition_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    seniority_level: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    tech_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
    )
    resume_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cover_letter_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cover_letter_used: Mapped[bool | None] = mapped_column(
        Boolean,
        default=None,
        nullable=True,
    )
    contacts_inline: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_action_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
    )
    attachments_links: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(
        BigInteger,
        default=1,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="applications")
    activities: Mapped[list[Activity]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )
    reminders: Mapped[list[Reminder]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "(salary_min IS NULL OR salary_max IS NULL) OR (salary_min <= salary_max)",
            name="ck_applications_salary_range",
        ),
        Index(
            "ix_applications_user_id_status",
            "user_id",
            "status",
        ),
        Index(
            "ix_applications_user_id_archived_at",
            "user_id",
            "archived_at",
        ),
        Index(
            "ix_applications_user_id_next_action_due",
            "user_id",
            "next_action_due",
        ),
        Index(
            "ix_applications_user_id_created_at_desc",
            "user_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_applications_tags_gin",
            "tags",
            postgresql_using="gin",
        ),
    )
