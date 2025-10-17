from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.activities import service as activities_service
from src.activities.models import ActivityStatus, ActivityType, InterviewStage
from src.applications import service as applications_service
from src.applications.models import AppStatus
from src.core.exceptions import ApplicationError, NotFoundError
from src.user.models import User


async def _seed_user_and_application(
    db: AsyncSession,
) -> tuple[User, UUID]:
    user = User(email="activities@example.com", password_hash="hash")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    application = await applications_service.create_application(
        db,
        user_id=user.id,
        data={
            "company": "Acme Corp",
            "role_title": "Backend Engineer",
            "status": AppStatus.APPLIED,
        },
    )
    return user, application.id


@pytest.mark.asyncio
async def test_list_activities_for_application(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)

    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    for idx in range(3):
        await activities_service.create_activity(
            async_db_session,
            user_id=user.id,
            application_id=application_id,
            data={
                "type": ActivityType.INTERVIEW,
                "status": ActivityStatus.SCHEDULED,
                "starts_at": starts_at + timedelta(hours=idx),
            },
        )

    activities = await activities_service.list_activities_for_application(
        async_db_session,
        user_id=user.id,
        application_id=application_id,
    )
    assert len(activities) == 3
    assert activities[0].application_id == application_id


@pytest.mark.asyncio
async def test_create_activity(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)

    activity = await activities_service.create_activity(
        async_db_session,
        user_id=user.id,
        application_id=application_id,
        data={
            "type": ActivityType.INTERVIEW,
            "status": ActivityStatus.SCHEDULED,
            "starts_at": datetime.now(timezone.utc) + timedelta(days=2),
            "interview_stage": InterviewStage.SCREENING,
        },
    )
    assert activity.id is not None
    assert activity.application_id == application_id
    assert activity.type == ActivityType.INTERVIEW


@pytest.mark.asyncio
async def test_update_activity_version_conflict(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)

    activity = await activities_service.create_activity(
        async_db_session,
        user_id=user.id,
        application_id=application_id,
        data={
            "type": ActivityType.INTERVIEW,
            "status": ActivityStatus.SCHEDULED,
            "starts_at": datetime.now(timezone.utc) + timedelta(hours=1),
        },
    )

    current_version = activity.version

    updated = await activities_service.update_activity(
        async_db_session,
        user_id=user.id,
        activity_id=activity.id,
        update_data={"status": ActivityStatus.DONE},
        if_match=str(current_version),
    )
    assert updated.status == ActivityStatus.DONE
    assert updated.version == current_version + 1

    with pytest.raises(ApplicationError) as exc:
        await activities_service.update_activity(
            async_db_session,
            user_id=user.id,
            activity_id=activity.id,
            update_data={"status": ActivityStatus.CANCELED},
            if_match=str(current_version),
        )
    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_update_activity_not_owned(async_db_session: AsyncSession):
    owner, application_id = await _seed_user_and_application(async_db_session)
    other_user = User(email="other@example.com", password_hash="hash")
    async_db_session.add(other_user)
    await async_db_session.commit()
    await async_db_session.refresh(other_user)

    activity = await activities_service.create_activity(
        async_db_session,
        user_id=owner.id,
        application_id=application_id,
        data={
            "type": ActivityType.CALL,
            "status": ActivityStatus.SCHEDULED,
            "starts_at": datetime.now(timezone.utc) + timedelta(hours=2),
        },
    )

    with pytest.raises(NotFoundError):
        await activities_service.update_activity(
            async_db_session,
            user_id=other_user.id,
            activity_id=activity.id,
            update_data={"status": ActivityStatus.DONE},
            if_match=str(activity.version),
        )


@pytest.mark.asyncio
async def test_delete_activity(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)

    activity = await activities_service.create_activity(
        async_db_session,
        user_id=user.id,
        application_id=application_id,
        data={
            "type": ActivityType.CALL,
            "status": ActivityStatus.SCHEDULED,
            "starts_at": datetime.now(timezone.utc) + timedelta(hours=2),
        },
    )

    await activities_service.delete_activity(
        async_db_session,
        user_id=user.id,
        activity_id=activity.id,
        if_match=str(activity.version),
    )

    with pytest.raises(NotFoundError):
        await activities_service.get_activity(
            async_db_session,
            user_id=user.id,
            activity_id=activity.id,
        )


@pytest.mark.asyncio
async def test_delete_activity_version_conflict(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)

    activity = await activities_service.create_activity(
        async_db_session,
        user_id=user.id,
        application_id=application_id,
        data={
            "type": ActivityType.EMAIL,
            "status": ActivityStatus.SCHEDULED,
            "starts_at": datetime.now(timezone.utc) + timedelta(hours=3),
        },
    )

    with pytest.raises(ApplicationError) as exc:
        await activities_service.delete_activity(
            async_db_session,
            user_id=user.id,
            activity_id=activity.id,
            if_match=str(activity.version + 1),
        )
    assert exc.value.status_code == status.HTTP_409_CONFLICT
