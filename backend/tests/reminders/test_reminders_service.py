from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications import service as applications_service
from src.applications.models import AppStatus
from src.core.exceptions import ApplicationError, NotFoundError
from src.reminders import service as reminders_service
from src.reminders.models import ReminderChannel
from src.user.models import User


async def _seed_user_and_application(db: AsyncSession) -> tuple[User, UUID]:
    user = User(email="reminders@example.com", password_hash="hash")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    application = await applications_service.create_application(
        db,
        user_id=user.id,
        data={
            "company": "Reminder Corp",
            "role_title": "Automation Engineer",
            "status": AppStatus.APPLIED,
        },
    )
    return user, application.id


@pytest.mark.asyncio
async def test_list_reminders_filters(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)
    now = datetime.now(timezone.utc)

    early_due = now + timedelta(hours=12)
    late_due = now + timedelta(days=2)

    first = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Follow up recruiter",
            "due_at": early_due,
            "channels": [ReminderChannel.EMAIL],
            "application_id": application_id,
        },
    )
    second = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Prep onsite",
            "due_at": late_due,
            "channels": [ReminderChannel.IN_APP],
            "application_id": application_id,
        },
    )

    await reminders_service.update_reminder(
        async_db_session,
        user_id=user.id,
        reminder_id=second.id,
        update_data={"sent": True, "sent_at": now + timedelta(hours=1)},
        if_match=str(second.version),
    )

    due_before = await reminders_service.list_reminders(
        async_db_session,
        user_id=user.id,
        due_before=early_due + timedelta(minutes=1),
    )
    assert len(due_before) == 1
    assert due_before[0].id == first.id

    due_after = await reminders_service.list_reminders(
        async_db_session,
        user_id=user.id,
        due_after=now + timedelta(days=1),
    )
    assert len(due_after) == 1
    assert due_after[0].id == second.id

    sent_only = await reminders_service.list_reminders(
        async_db_session,
        user_id=user.id,
        sent=True,
    )
    assert len(sent_only) == 1
    assert sent_only[0].id == second.id


@pytest.mark.asyncio
async def test_create_reminder(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)
    due_at = datetime.now(timezone.utc) + timedelta(days=1)

    reminder = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Submit take-home",
            "due_at": due_at,
            "application_id": application_id,
            "channels": [ReminderChannel.IN_APP, ReminderChannel.EMAIL],
        },
    )
    assert reminder.id is not None
    assert reminder.due_at == due_at
    assert reminder.application_id == application_id


@pytest.mark.asyncio
async def test_update_reminder_version_conflict(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)
    due_at = datetime.now(timezone.utc) + timedelta(hours=6)

    reminder = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Send thank-you email",
            "due_at": due_at,
            "application_id": application_id,
        },
    )
    current_version = reminder.version

    updated = await reminders_service.update_reminder(
        async_db_session,
        user_id=user.id,
        reminder_id=reminder.id,
        update_data={"title": "Send detailed thank-you email"},
        if_match=str(current_version),
    )
    assert updated.title.startswith("Send detailed")
    assert updated.version == current_version + 1

    with pytest.raises(ApplicationError):
        await reminders_service.update_reminder(
            async_db_session,
            user_id=user.id,
            reminder_id=reminder.id,
            update_data={"title": "Another change"},
            if_match=str(current_version),
        )


@pytest.mark.asyncio
async def test_delete_reminder(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)

    reminder = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Draft follow-up",
            "due_at": datetime.now(timezone.utc) + timedelta(days=3),
            "application_id": application_id,
        },
    )

    await reminders_service.delete_reminder(
        async_db_session,
        user_id=user.id,
        reminder_id=reminder.id,
        if_match=str(reminder.version),
    )

    with pytest.raises(NotFoundError):
        await reminders_service.get_reminder(
            async_db_session,
            user_id=user.id,
            reminder_id=reminder.id,
        )


@pytest.mark.asyncio
async def test_delete_reminder_version_conflict(async_db_session: AsyncSession):
    user, application_id = await _seed_user_and_application(async_db_session)

    reminder = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Conflict reminder",
            "due_at": datetime.now(timezone.utc) + timedelta(days=4),
            "application_id": application_id,
        },
    )

    with pytest.raises(ApplicationError):
        await reminders_service.delete_reminder(
            async_db_session,
            user_id=user.id,
            reminder_id=reminder.id,
            if_match=str(reminder.version + 1),
        )
