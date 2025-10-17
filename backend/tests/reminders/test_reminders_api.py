from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications import service as applications_service
from src.auth import utils as auth_utils
from src.reminders.models import ReminderChannel
from src.user.models import User


async def _create_user(async_db_session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="hash")
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    return user


def _auth_header(email: str) -> dict[str, str]:
    token = auth_utils.create_access_token(data={"sub": email})
    return {"Authorization": f"Bearer {token}"}


async def _create_application(async_db_session: AsyncSession, user_id) -> str:
    application = await applications_service.create_application(
        async_db_session,
        user_id=user_id,
        data={
            "company": "Reminder API Corp",
            "role_title": "Reminder Tester",
        },
    )
    return str(application.id)


@pytest.mark.asyncio
async def test_reminders_list_filters(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "reminder-api@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)
    now = datetime.now(timezone.utc)

    for offset, title in ((6, "AM ping"), (30, "Later ping")):
        payload = {
            "title": title,
            "due_at": (now + timedelta(hours=offset)).isoformat(),
            "application_id": application_id,
            "channels": [ReminderChannel.IN_APP.value],
        }
        resp = await client.post("/reminders", json=payload, headers=headers)
        assert resp.status_code == status.HTTP_201_CREATED

    resp = await client.get(
        "/reminders",
        params={"due_before": (now + timedelta(hours=8)).isoformat()},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_reminder_crud_flow(client: AsyncClient, async_db_session: AsyncSession):
    user = await _create_user(async_db_session, "reminder-crud@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)

    reminder_id = str(uuid4())
    due_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {
        "id": reminder_id,
        "title": "Send feedback",
        "due_at": due_at,
        "application_id": application_id,
        "channels": [ReminderChannel.EMAIL.value],
    }
    resp = await client.post("/reminders", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    etag = resp.headers["ETag"]

    resp = await client.get(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["title"] == "Send feedback"

    resp = await client.patch(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        json={"sent": True, "sent_at": datetime.now(timezone.utc).isoformat()},
        headers={**headers, "If-Match": etag},
    )
    assert resp.status_code == status.HTTP_200_OK
    new_etag = resp.headers["ETag"]
    assert new_etag != etag

    resp = await client.delete(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        headers={**headers, "If-Match": new_etag},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    resp = await client.get(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_reminder_version_conflict(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "reminder-conflict@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)

    resp = await client.post(
        "/reminders",
        json={
            "title": "Conflict reminder",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat(),
            "application_id": application_id,
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_201_CREATED
    reminder_id = resp.json()["id"]
    etag = resp.headers["ETag"]

    resp = await client.patch(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        json={"title": "Updated title"},
        headers={**headers, "If-Match": etag},
    )
    assert resp.status_code == status.HTTP_200_OK
    updated_etag = resp.headers["ETag"]

    resp = await client.patch(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        json={"title": "Stale update"},
        headers={**headers, "If-Match": etag},
    )
    assert resp.status_code == status.HTTP_409_CONFLICT

    resp = await client.delete(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        headers={**headers, "If-Match": etag},
    )
    assert resp.status_code == status.HTTP_409_CONFLICT

    resp = await client.delete(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        headers={**headers, "If-Match": updated_etag},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_reminder_missing_if_match(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "reminder-missing-ifmatch@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)

    resp = await client.post(
        "/reminders",
        json={
            "title": "Missing header",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat(),
            "application_id": application_id,
        },
        headers=headers,
    )
    reminder_id = resp.json()["id"]
    etag = resp.headers["ETag"]

    resp = await client.patch(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        json={"title": "New title"},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    resp = await client.delete(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    resp = await client.delete(
        "/reminders/detail",
        params={"reminder_id": reminder_id},
        headers={**headers, "If-Match": etag},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
