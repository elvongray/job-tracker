from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ApplicationError, InvalidRequestError, NotFoundError
from src.reminders.models import Reminder
from src.reminders.utils import parse_if_match

logger = logging.getLogger(__name__)


async def list_reminders(
    db: AsyncSession,
    *,
    user_id: UUID,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    sent: bool | None = None,
) -> list[Reminder]:
    logger.debug(
        "Listing reminders",
        extra={
            "user_id": str(user_id),
            "due_before": due_before.isoformat() if due_before else None,
            "due_after": due_after.isoformat() if due_after else None,
            "sent": sent,
        },
    )
    query = (
        select(Reminder)
        .where(Reminder.user_id == user_id)
        .order_by(Reminder.due_at.asc())
    )
    if due_before:
        query = query.where(Reminder.due_at <= due_before)
    if due_after:
        query = query.where(Reminder.due_at >= due_after)
    if sent is not None:
        query = query.where(Reminder.sent.is_(sent))
    result = await db.execute(query)
    reminders = result.scalars().all()
    logger.debug(
        "Fetched reminders",
        extra={"user_id": str(user_id), "count": len(reminders)},
    )
    return list(reminders)


async def create_reminder(
    db: AsyncSession,
    *,
    user_id: UUID,
    data: dict,
) -> Reminder:
    payload = {key: value for key, value in data.items() if value is not None}
    reminder = Reminder(user_id=user_id, **payload)
    if "id" in data and data["id"] is not None:
        reminder.id = data["id"]
    db.add(reminder)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise InvalidRequestError(
            "Unable to create reminder with provided data."
        ) from exc
    await db.refresh(reminder)
    logger.info(
        "Created reminder",
        extra={"user_id": str(user_id), "reminder_id": str(reminder.id)},
    )
    return reminder


async def get_reminder(
    db: AsyncSession,
    *,
    user_id: UUID,
    reminder_id: UUID,
) -> Reminder:
    query = select(Reminder).where(
        Reminder.id == reminder_id, Reminder.user_id == user_id
    )
    result = await db.execute(query)
    reminder = result.scalars().first()
    if not reminder:
        logger.warning(
            "Reminder not found",
            extra={"user_id": str(user_id), "reminder_id": str(reminder_id)},
        )
        raise NotFoundError(
            "Reminder not found.",
            meta={"resource": "reminders", "id": str(reminder_id)},
        )
    logger.debug(
        "Loaded reminder",
        extra={"user_id": str(user_id), "reminder_id": str(reminder_id)},
    )
    return reminder


async def update_reminder(
    db: AsyncSession,
    *,
    user_id: UUID,
    reminder_id: UUID,
    update_data: dict,
    if_match: str | None,
) -> Reminder:
    expected_version = parse_if_match(if_match)
    reminder = await get_reminder(db, user_id=user_id, reminder_id=reminder_id)
    if reminder.version != expected_version:
        logger.warning(
            "Version conflict on reminder update",
            extra={
                "user_id": str(user_id),
                "reminder_id": str(reminder_id),
                "expected_version": expected_version,
                "current_version": reminder.version,
            },
        )
        raise ApplicationError(
            "Row version does not match If-Match header.",
            status_code=status.HTTP_409_CONFLICT,
            title="Version Conflict",
            error_type="https://errors.jobtracker.app/conflict",
            meta={
                "resource": "reminders",
                "id": str(reminder_id),
                "current_version": reminder.version,
            },
        )
    if update_data:
        for field, value in update_data.items():
            setattr(reminder, field, value)
        reminder.version += 1
        await db.commit()
        await db.refresh(reminder)
        logger.info(
            "Updated reminder",
            extra={
                "user_id": str(user_id),
                "reminder_id": str(reminder_id),
                "version": reminder.version,
            },
        )
    return reminder


async def delete_reminder(
    db: AsyncSession,
    *,
    user_id: UUID,
    reminder_id: UUID,
    if_match: str | None,
) -> None:
    expected_version = parse_if_match(if_match)
    reminder = await get_reminder(db, user_id=user_id, reminder_id=reminder_id)
    if reminder.version != expected_version:
        logger.warning(
            "Version conflict on reminder delete",
            extra={
                "user_id": str(user_id),
                "reminder_id": str(reminder_id),
                "expected_version": expected_version,
                "current_version": reminder.version,
            },
        )
        raise ApplicationError(
            "Row version does not match If-Match header.",
            status_code=status.HTTP_409_CONFLICT,
            title="Version Conflict",
            error_type="https://errors.jobtracker.app/conflict",
            meta={
                "resource": "reminders",
                "id": str(reminder_id),
                "current_version": reminder.version,
            },
        )
    await db.delete(reminder)
    await db.commit()
    logger.info(
        "Deleted reminder",
        extra={"user_id": str(user_id), "reminder_id": str(reminder_id)},
    )
