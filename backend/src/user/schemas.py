from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserSettings(BaseModel):
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    reminder_defaults: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    id: UUID
    email: str
    password_hash: str | None = Field(default=None, repr=False)
    display_name: str | None = None
    timezone: str = "Africa/Lagos"
    email_verified_at: datetime | None = None
    session_timeout_mins: int = 4320
    is_active: bool = True
    settings: UserSettings | None = None

    model_config = ConfigDict(from_attributes=True)
