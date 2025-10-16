from __future__ import annotations

import logging
from uuid import UUID

from fastapi import status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.applications.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.applications.models import Application, AppStatus, PriorityLevel
from src.applications.utils import decode_cursor, encode_cursor, parse_if_match
from src.core.exceptions import ApplicationError, InvalidRequestError, NotFoundError

logger = logging.getLogger(__name__)


async def list_applications(
    db: AsyncSession,
    *,
    user_id: UUID,
    limit: int = DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    status_filter: AppStatus | None = None,
    q: str | None = None,
    tag: str | None = None,
    priority: PriorityLevel | None = None,
    archived: bool | None = None,
) -> tuple[list[Application], str | None]:
    if limit <= 0:
        raise InvalidRequestError("limit must be greater than zero.")
    if limit > MAX_PAGE_SIZE:
        raise InvalidRequestError(f"limit cannot exceed {MAX_PAGE_SIZE}.")

    logger.debug(
        "Listing applications",
        extra={
            "user_id": str(user_id),
            "limit": limit,
            "cursor": cursor,
            "status": status_filter.value if status_filter else None,
            "tag": tag,
            "priority": priority.value if priority else None,
            "archived": archived,
        },
    )

    query = (
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc(), Application.id.desc())
        .options(
            selectinload(Application.activities), selectinload(Application.reminders)
        )
    )

    if cursor:
        created_at_cursor, id_cursor = decode_cursor(cursor)
        query = query.where(
            or_(
                Application.created_at < created_at_cursor,
                and_(
                    Application.created_at == created_at_cursor,
                    Application.id < id_cursor,
                ),
            )
        )

    if status_filter:
        query = query.where(Application.status == status_filter)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Application.company.ilike(pattern),
                Application.role_title.ilike(pattern),
                func.coalesce(Application.notes, "").ilike(pattern),
            )
        )

    if tag:
        query = query.where(Application.tags.any(tag))

    if priority:
        query = query.where(Application.priority == priority)

    if archived is True:
        query = query.where(Application.archived_at.is_not(None))
    elif archived is False:
        query = query.where(Application.archived_at.is_(None))

    query = query.limit(limit + 1)
    result = await db.execute(query)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    applications = rows[:limit]
    next_cursor = encode_cursor(applications[-1]) if has_more and applications else None

    logger.debug(
        "Fetched applications",
        extra={
            "user_id": str(user_id),
            "count": len(applications),
            "next_cursor": next_cursor,
        },
    )
    return list(applications), next_cursor


async def create_application(
    db: AsyncSession,
    *,
    user_id: UUID,
    data: dict,
) -> Application:
    payload = {key: value for key, value in data.items() if value is not None}
    application = Application(user_id=user_id, **payload)
    if "id" in data and data["id"] is not None:
        application.id = data["id"]
    db.add(application)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise InvalidRequestError(
            "Unable to create application with provided data."
        ) from exc
    await db.refresh(application)
    logger.info(
        "Created application",
        extra={"user_id": str(user_id), "application_id": str(application.id)},
    )
    return application


async def get_application(
    db: AsyncSession,
    *,
    user_id: UUID,
    application_id: UUID,
    eager: bool = True,
) -> Application:
    query = select(Application).where(
        Application.id == application_id,
        Application.user_id == user_id,
    )
    if eager:
        query = query.options(
            selectinload(Application.activities),
            selectinload(Application.reminders),
        )
    result = await db.execute(query)
    application = result.scalars().first()
    if not application:
        logger.warning(
            "Application not found",
            extra={"user_id": str(user_id), "application_id": str(application_id)},
        )
        raise NotFoundError(
            "Application not found.",
            meta={"resource": "applications", "id": str(application_id)},
        )
    logger.debug(
        "Loaded application",
        extra={"user_id": str(user_id), "application_id": str(application_id)},
    )
    return application


async def update_application(
    db: AsyncSession,
    *,
    user_id: UUID,
    application_id: UUID,
    update_data: dict,
    if_match: str | None,
) -> Application:
    expected_version = parse_if_match(if_match)
    application = await get_application(
        db, user_id=user_id, application_id=application_id, eager=False
    )
    if application.version != expected_version:
        logger.warning(
            "Version conflict on application update",
            extra={
                "user_id": str(user_id),
                "application_id": str(application_id),
                "expected_version": expected_version,
                "current_version": application.version,
            },
        )
        raise ApplicationError(
            "Row version does not match If-Match header.",
            status_code=status.HTTP_409_CONFLICT,
            title="Version Conflict",
            error_type="https://errors.jobtracker.app/conflict",
            meta={
                "resource": "applications",
                "id": str(application_id),
                "current_version": application.version,
            },
        )

    if update_data:
        for field, value in update_data.items():
            setattr(application, field, value)
        application.version += 1
        await db.commit()
        await db.refresh(application)
        logger.info(
            "Updated application",
            extra={
                "user_id": str(user_id),
                "application_id": str(application_id),
                "version": application.version,
            },
        )
    return application


async def delete_application(
    db: AsyncSession,
    *,
    user_id: UUID,
    application_id: UUID,
    if_match: str | None,
) -> None:
    expected_version = parse_if_match(if_match)
    application = await get_application(
        db, user_id=user_id, application_id=application_id, eager=False
    )
    if application.version != expected_version:
        logger.warning(
            "Version conflict on application delete",
            extra={
                "user_id": str(user_id),
                "application_id": str(application_id),
                "expected_version": expected_version,
                "current_version": application.version,
            },
        )
        raise ApplicationError(
            "Row version does not match If-Match header.",
            status_code=status.HTTP_409_CONFLICT,
            title="Version Conflict",
            error_type="https://errors.jobtracker.app/conflict",
            meta={
                "resource": "applications",
                "id": str(application_id),
                "current_version": application.version,
            },
        )
    await db.delete(application)
    await db.commit()
    logger.info(
        "Deleted application",
        extra={"user_id": str(user_id), "application_id": str(application_id)},
    )
