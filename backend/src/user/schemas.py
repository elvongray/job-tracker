from __future__ import annotations

from datetime import datetime, time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserSettings(BaseModel):
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    reminder_defaults: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    timezone: str | None = None
    session_timeout_mins: int | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    timezone: str | None = None
    session_timeout_mins: int | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    password_hash: str | None = Field(default=None, repr=False)
    display_name: str | None = None
    timezone: str = "Africa/Lagos"
    email_verified_at: datetime | None = None
    session_timeout_mins: int = 4320
    is_active: bool = True
    settings: UserSettings | None = None

    model_config = ConfigDict(from_attributes=True)


# Backwards compatibility for existing imports
User = UserRead
