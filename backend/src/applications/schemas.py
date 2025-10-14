from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict

from src.applications.models import AppStatus, LocationMode, PriorityLevel


class ApplicationBase(BaseModel):
    company: str
    role_title: str
    source: str | None = "Other"
    status: AppStatus = AppStatus.APPLIED
    application_date: date | None = None
    priority: PriorityLevel = PriorityLevel.NONE
    location_mode: LocationMode = LocationMode.REMOTE
    location_text: str | None = None
    timezone: str | None = None
    job_url: AnyUrl | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    job_requisition_id: str | None = None
    seniority_level: str | None = None
    tech_keywords: list[str] | None = None
    resume_url: AnyUrl | None = None
    cover_letter_url: AnyUrl | None = None
    cover_letter_used: bool | None = None
    contacts_inline: dict[str, Any] | None = None
    next_action: str | None = None
    next_action_due: datetime | None = None
    notes: str | None = None
    tags: list[str] | None = None
    attachments_links: list[AnyUrl] | None = None
    archived_at: datetime | None = None


class ApplicationCreate(ApplicationBase):
    id: UUID | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role_title: str | None = None
    source: str | None = None
    status: AppStatus | None = None
    application_date: date | None = None
    priority: PriorityLevel | None = None
    location_mode: LocationMode | None = None
    location_text: str | None = None
    timezone: str | None = None
    job_url: AnyUrl | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    job_requisition_id: str | None = None
    seniority_level: str | None = None
    tech_keywords: list[str] | None = None
    resume_url: AnyUrl | None = None
    cover_letter_url: AnyUrl | None = None
    cover_letter_used: bool | None = None
    contacts_inline: dict[str, Any] | None = None
    next_action: str | None = None
    next_action_due: datetime | None = None
    notes: str | None = None
    tags: list[str] | None = None
    attachments_links: list[AnyUrl] | None = None
    archived_at: datetime | None = None


class ApplicationOut(ApplicationBase):
    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationSummary(BaseModel):
    id: UUID
    company: str
    role_title: str
    status: AppStatus
    priority: PriorityLevel
    next_action_due: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    items: list[ApplicationOut]
    next_cursor: str | None = None
