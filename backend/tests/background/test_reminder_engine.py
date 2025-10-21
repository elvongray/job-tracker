from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pytest

from src.applications import service as applications_service
from src.applications.models import AppStatus
from src.background.reminder_engine import process_due_reminders
from src.reminders import service as reminders_service
from src.reminders.models import ReminderChannel
from src.user.models import User, UserSettings


async def _create_user(
    async_db_session, email: str, timezone_name: str = "UTC"
) -> User:
    user = User(email=email, password_hash="hash", timezone=timezone_name)
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    return user


async def _create_application(async_db_session, user_id):
    application = await applications_service.create_application(
        async_db_session,
        user_id=user_id,
        data={
            "company": "ReminderSpec Corp",
            "role_title": "QA",
            "status": AppStatus.APPLIED,
        },
    )
    return application.id


@pytest.mark.asyncio
async def test_process_due_reminders_marks_sent(async_db_session):
    user = await _create_user(async_db_session, "engine@example.com")
    application_id = await _create_application(async_db_session, user.id)
    reminder = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Ping recruiter",
            "due_at": datetime.now(timezone.utc) - timedelta(minutes=1),
            "application_id": application_id,
            "channels": [ReminderChannel.IN_APP],
        },
    )

    result = await process_due_reminders(
        async_db_session, now=datetime.now(timezone.utc)
    )
    await async_db_session.refresh(reminder)

    assert result.sent == 1
    assert result.deferred == 0
    assert reminder.sent is True
    assert reminder.sent_at is not None
    assert reminder.meta["dispatched_channels"] == [ReminderChannel.IN_APP.value]


@pytest.mark.asyncio
async def test_process_due_reminders_defers_in_quiet_hours(async_db_session):
    user = await _create_user(async_db_session, "quiet@example.com")
    settings = UserSettings(
        user_id=user.id,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(6, 0),
    )
    async_db_session.add(settings)
    await async_db_session.commit()
    await async_db_session.refresh(user)

    application_id = await _create_application(async_db_session, user.id)
    reminder = await reminders_service.create_reminder(
        async_db_session,
        user_id=user.id,
        data={
            "title": "Late night email",
            "due_at": datetime(2025, 1, 1, 23, 0, tzinfo=timezone.utc),
            "application_id": application_id,
            "channels": [ReminderChannel.EMAIL],
        },
    )

    now = datetime(2025, 1, 1, 23, 0, tzinfo=timezone.utc)
    result = await process_due_reminders(async_db_session, now=now)
    await async_db_session.refresh(reminder)

    assert result.sent == 0
    assert result.deferred == 1
    assert reminder.sent is False
    assert reminder.due_at > now
