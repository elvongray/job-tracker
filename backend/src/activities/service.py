from __future__ import annotations

import logging
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.activities.models import Activity
from src.activities.utils import parse_if_match
from src.core.exceptions import ApplicationError, InvalidRequestError, NotFoundError

logger = logging.getLogger(__name__)


async def list_activities_for_application(
    db: AsyncSession,
    *,
    user_id: UUID,
    application_id: UUID,
) -> list[Activity]:
    logger.debug(
        "Listing activities",
        extra={"user_id": str(user_id), "application_id": str(application_id)},
    )
    query = (
        select(Activity)
        .where(
            Activity.user_id == user_id,
            Activity.application_id == application_id,
        )
        .order_by(Activity.starts_at.nulls_last(), Activity.created_at.desc())
        .options(selectinload(Activity.reminders))
    )
    result = await db.execute(query)
    activities = result.scalars().all()
    logger.debug(
        "Fetched activities",
        extra={
            "user_id": str(user_id),
            "application_id": str(application_id),
            "count": len(activities),
        },
    )
    return list(activities)


async def create_activity(
    db: AsyncSession,
    *,
    user_id: UUID,
    application_id: UUID,
    data: dict,
) -> Activity:
    payload = {key: value for key, value in data.items() if value is not None}
    activity = Activity(user_id=user_id, application_id=application_id, **payload)
    if "id" in data and data["id"] is not None:
        activity.id = data["id"]
    db.add(activity)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise InvalidRequestError(
            "Unable to create activity with provided data."
        ) from exc
    await db.refresh(activity)
    logger.info(
        "Created activity",
        extra={
            "user_id": str(user_id),
            "application_id": str(application_id),
            "activity_id": str(activity.id),
        },
    )
    return activity


async def get_activity(
    db: AsyncSession,
    *,
    user_id: UUID,
    activity_id: UUID,
    eager: bool = True,
) -> Activity:
    query = select(Activity).where(
        Activity.id == activity_id,
        Activity.user_id == user_id,
    )
    if eager:
        query = query.options(selectinload(Activity.reminders))
    result = await db.execute(query)
    activity = result.scalars().first()
    if not activity:
        logger.warning(
            "Activity not found",
            extra={"user_id": str(user_id), "activity_id": str(activity_id)},
        )
        raise NotFoundError(
            "Activity not found.",
            meta={"resource": "activities", "id": str(activity_id)},
        )
    logger.debug(
        "Loaded activity",
        extra={"user_id": str(user_id), "activity_id": str(activity_id)},
    )
    return activity


async def update_activity(
    db: AsyncSession,
    *,
    user_id: UUID,
    activity_id: UUID,
    update_data: dict,
    if_match: str | None,
) -> Activity:
    expected_version = parse_if_match(if_match)
    activity = await get_activity(
        db, user_id=user_id, activity_id=activity_id, eager=False
    )
    if activity.version != expected_version:
        logger.warning(
            "Version conflict on activity update",
            extra={
                "user_id": str(user_id),
                "activity_id": str(activity_id),
                "expected_version": expected_version,
                "current_version": activity.version,
            },
        )
        raise ApplicationError(
            "Row version does not match If-Match header.",
            status_code=status.HTTP_409_CONFLICT,
            title="Version Conflict",
            error_type="https://errors.jobtracker.app/conflict",
            meta={
                "resource": "activities",
                "id": str(activity_id),
                "current_version": activity.version,
            },
        )
    if update_data:
        for field, value in update_data.items():
            setattr(activity, field, value)
        activity.version += 1
        await db.commit()
        await db.refresh(activity)
        logger.info(
            "Updated activity",
            extra={
                "user_id": str(user_id),
                "activity_id": str(activity_id),
                "version": activity.version,
            },
        )
    return activity


async def delete_activity(
    db: AsyncSession,
    *,
    user_id: UUID,
    activity_id: UUID,
    if_match: str | None,
) -> None:
    expected_version = parse_if_match(if_match)
    activity = await get_activity(
        db, user_id=user_id, activity_id=activity_id, eager=False
    )
    if activity.version != expected_version:
        logger.warning(
            "Version conflict on activity delete",
            extra={
                "user_id": str(user_id),
                "activity_id": str(activity_id),
                "expected_version": expected_version,
                "current_version": activity.version,
            },
        )
        raise ApplicationError(
            "Row version does not match If-Match header.",
            status_code=status.HTTP_409_CONFLICT,
            title="Version Conflict",
            error_type="https://errors.jobtracker.app/conflict",
            meta={
                "resource": "activities",
                "id": str(activity_id),
                "current_version": activity.version,
            },
        )
    await db.delete(activity)
    await db.commit()
    logger.info(
        "Deleted activity",
        extra={"user_id": str(user_id), "activity_id": str(activity_id)},
    )
