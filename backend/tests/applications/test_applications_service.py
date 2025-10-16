from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications import service as applications_service
from src.applications.models import AppStatus, PriorityLevel
from src.core.exceptions import ApplicationError, InvalidRequestError, NotFoundError
from src.user.models import User


@pytest.mark.asyncio
async def test_list_applications_pagination(async_db_session: AsyncSession):
    user = User(email="pagination@example.com", password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    for idx in range(3):
        await applications_service.create_application(
            async_db_session,
            user_id=user.id,
            data={
                "company": f"Company {idx}",
                "role_title": f"Role {idx}",
                "tags": [f"tag{idx}"],
            },
        )

    first_page, cursor = await applications_service.list_applications(
        async_db_session,
        user_id=user.id,
        limit=2,
    )
    assert len(first_page) == 2
    assert cursor is not None

    second_page, next_cursor = await applications_service.list_applications(
        async_db_session,
        user_id=user.id,
        limit=2,
        cursor=cursor,
    )
    assert len(second_page) == 1
    assert next_cursor is None


@pytest.mark.asyncio
async def test_list_applications_filters(async_db_session: AsyncSession):
    user = User(email="filters@example.com", password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    await applications_service.create_application(
        async_db_session,
        user_id=user.id,
        data={
            "company": "Acme Corp",
            "role_title": "Backend Engineer",
            "status": AppStatus.SCREENING,
            "tags": ["python", "backend"],
            "priority": PriorityLevel.HIGH,
            "notes": "Important opportunity",
        },
    )
    await applications_service.create_application(
        async_db_session,
        user_id=user.id,
        data={
            "company": "Serenity Systems",
            "role_title": "Frontend Engineer",
            "status": AppStatus.APPLIED,
            "tags": ["frontend"],
            "priority": PriorityLevel.LOW,
            "archived_at": datetime.now(timezone.utc),
        },
    )

    filtered_by_status, _ = await applications_service.list_applications(
        async_db_session,
        user_id=user.id,
        status_filter=AppStatus.SCREENING,
    )
    assert len(filtered_by_status) == 1
    assert filtered_by_status[0].company == "Acme Corp"

    filtered_by_tag, _ = await applications_service.list_applications(
        async_db_session,
        user_id=user.id,
        tag="python",
    )
    assert len(filtered_by_tag) == 1
    assert "python" in filtered_by_tag[0].tags

    filtered_by_priority, _ = await applications_service.list_applications(
        async_db_session,
        user_id=user.id,
        priority=PriorityLevel.HIGH,
    )
    assert len(filtered_by_priority) == 1
    assert filtered_by_priority[0].priority == PriorityLevel.HIGH

    filtered_archived, _ = await applications_service.list_applications(
        async_db_session,
        user_id=user.id,
        archived=True,
    )
    assert len(filtered_archived) == 1
    assert filtered_archived[0].company == "Serenity Systems"


@pytest.mark.asyncio
async def test_update_application_version_conflict(async_db_session: AsyncSession):
    user = User(email="versions@example.com", password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    application = await applications_service.create_application(
        async_db_session,
        user_id=user.id,
        data={
            "company": "FutureTech",
            "role_title": "Data Scientist",
        },
    )

    current_version = application.version

    updated = await applications_service.update_application(
        async_db_session,
        user_id=user.id,
        application_id=application.id,
        update_data={"status": AppStatus.SCREENING},
        if_match=str(current_version),
    )
    assert updated.status == AppStatus.SCREENING
    assert updated.version == current_version + 1

    with pytest.raises(ApplicationError) as exc:
        await applications_service.update_application(
            async_db_session,
            user_id=user.id,
            application_id=application.id,
            update_data={"status": AppStatus.INTERVIEW_LOOP},
            if_match=str(current_version),
        )
    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_get_application_not_found(async_db_session: AsyncSession):
    user = User(email="missing@example.com", password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    missing_id = uuid4()
    with pytest.raises(NotFoundError):
        await applications_service.get_application(
            async_db_session,
            user_id=user.id,
            application_id=missing_id,
        )


@pytest.mark.asyncio
async def test_delete_application_with_version_conflict(async_db_session: AsyncSession):
    user = User(email="delete-conflict@example.com", password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    application = await applications_service.create_application(
        async_db_session,
        user_id=user.id,
        data={"company": "ConflictCo", "role_title": "Engineer"},
    )

    current_version = application.version

    await applications_service.update_application(
        async_db_session,
        user_id=user.id,
        application_id=application.id,
        update_data={"status": AppStatus.SCREENING},
        if_match=str(application.version),
    )

    with pytest.raises(ApplicationError):
        await applications_service.delete_application(
            async_db_session,
            user_id=user.id,
            application_id=application.id,
            if_match=str(current_version),
        )


@pytest.mark.asyncio
async def test_delete_application_success(async_db_session: AsyncSession):
    user = User(email="delete-success@example.com", password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    application = await applications_service.create_application(
        async_db_session,
        user_id=user.id,
        data={"company": "RemoveMe Inc.", "role_title": "QA"},
    )

    await applications_service.delete_application(
        async_db_session,
        user_id=user.id,
        application_id=application.id,
        if_match=str(application.version),
    )

    with pytest.raises(NotFoundError):
        await applications_service.get_application(
            async_db_session,
            user_id=user.id,
            application_id=application.id,
        )


@pytest.mark.asyncio
async def test_list_applications_invalid_cursor(async_db_session: AsyncSession):
    user = User(email="cursor-invalid@example.com", password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    with pytest.raises(InvalidRequestError):
        await applications_service.list_applications(
            async_db_session,
            user_id=user.id,
            cursor="invalid!!",
        )
