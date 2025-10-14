from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.activities.models import (
    ActivityStatus,
    ActivityType,
    FollowupChannel,
    InterviewMedium,
    InterviewStage,
)


class ActivityBase(BaseModel):
    type: ActivityType
    status: ActivityStatus = ActivityStatus.SCHEDULED
    starts_at: datetime | None = None
    duration_minutes: int | None = None
    timezone: str | None = None
    outcome: str | None = None
    next_action: str | None = None
    next_action_due: datetime | None = None
    notes: str | None = None
    related_contacts: dict[str, Any] | None = None

    interview_stage: InterviewStage | None = None
    interview_medium: InterviewMedium | None = None
    location_or_link: str | None = None
    agenda: str | None = None
    prep_checklist: dict[str, Any] | None = None

    followup_channel: FollowupChannel | None = None
    template_used: str | None = None
    reply_deadline: datetime | None = None


class ActivityCreate(ActivityBase):
    id: UUID | None = None


class ActivityUpdate(BaseModel):
    status: ActivityStatus | None = None
    starts_at: datetime | None = None
    duration_minutes: int | None = None
    timezone: str | None = None
    outcome: str | None = None
    next_action: str | None = None
    next_action_due: datetime | None = None
    notes: str | None = None
    related_contacts: dict[str, Any] | None = None
    interview_stage: InterviewStage | None = None
    interview_medium: InterviewMedium | None = None
    location_or_link: str | None = None
    agenda: str | None = None
    prep_checklist: dict[str, Any] | None = None
    followup_channel: FollowupChannel | None = None
    template_used: str | None = None
    reply_deadline: datetime | None = None


class ActivityOut(ActivityBase):
    id: UUID
    application_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
