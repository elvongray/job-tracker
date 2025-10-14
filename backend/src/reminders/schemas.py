from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.reminders.models import ReminderChannel


def _default_channels() -> list[ReminderChannel]:
    return [ReminderChannel.IN_APP]


class ReminderBase(BaseModel):
    title: str
    due_at: datetime
    channels: list[ReminderChannel] = Field(default_factory=_default_channels)
    application_id: UUID | None = None
    activity_id: UUID | None = None
    meta: dict[str, Any] | None = None


class ReminderCreate(ReminderBase):
    id: UUID | None = None


class ReminderUpdate(BaseModel):
    title: str | None = None
    due_at: datetime | None = None
    channels: list[ReminderChannel] | None = None
    application_id: UUID | None = None
    activity_id: UUID | None = None
    meta: dict[str, Any] | None = None
    sent: bool | None = None


class ReminderOut(ReminderBase):
    id: UUID
    version: int
    sent: bool
    sent_at: datetime | None = None
    dedupe_key: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
