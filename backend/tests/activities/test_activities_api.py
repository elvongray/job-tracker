from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.activities.models import ActivityStatus, ActivityType
from src.applications import service as applications_service
from src.auth import utils as auth_utils
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


async def _create_application(async_db_session: AsyncSession, user_id: UUID) -> UUID:
    application = await applications_service.create_application(
        async_db_session,
        user_id=user_id,
        data={
            "company": "API Corp",
            "role_title": "Integration Tester",
        },
    )
    return application.id


@pytest.mark.asyncio
async def test_list_activities_api(client: AsyncClient, async_db_session: AsyncSession):
    user = await _create_user(async_db_session, "activity-api@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)

    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    for idx in range(2):
        payload = {
            "type": ActivityType.INTERVIEW.value,
            "status": ActivityStatus.SCHEDULED.value,
            "starts_at": (starts_at + timedelta(hours=idx)).isoformat(),
        }
        response = await client.post(
            "/activities",
            params={"application_id": str(application_id)},
            json=payload,
            headers=headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

    response = await client.get(
        "/activities",
        params={"application_id": str(application_id)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_activity_crud_flow(client: AsyncClient, async_db_session: AsyncSession):
    user = await _create_user(async_db_session, "activity-crud@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)

    activity_id = uuid4()
    payload = {
        "id": str(activity_id),
        "type": ActivityType.CALL.value,
        "status": ActivityStatus.SCHEDULED.value,
        "starts_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    }
    response = await client.post(
        "/activities",
        params={"application_id": str(application_id)},
        json=payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    etag = response.headers["ETag"]

    response = await client.get(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": str(activity_id),
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["type"] == ActivityType.CALL.value

    response = await client.patch(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": str(activity_id),
        },
        json={
            "status": ActivityStatus.DONE.value,
            "starts_at": (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(),
        },
        headers={**headers, "If-Match": etag},
    )
    assert response.status_code == status.HTTP_200_OK
    new_etag = response.headers["ETag"]
    assert new_etag != etag

    response = await client.delete(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": str(activity_id),
        },
        headers={**headers, "If-Match": new_etag},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await client.get(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": str(activity_id),
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_activity_version_conflict_api(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "activity-conflict@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)

    response = await client.post(
        "/activities",
        params={"application_id": str(application_id)},
        json={
            "type": ActivityType.EMAIL.value,
            "status": ActivityStatus.SCHEDULED.value,
            "starts_at": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    activity_id = response.json()["id"]
    initial_etag = response.headers["ETag"]

    response = await client.patch(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": activity_id,
        },
        json={
            "status": ActivityStatus.DONE.value,
            "starts_at": (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat(),
        },
        headers={**headers, "If-Match": initial_etag},
    )
    assert response.status_code == status.HTTP_200_OK
    updated_etag = response.headers["ETag"]

    response = await client.patch(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": activity_id,
        },
        json={
            "status": ActivityStatus.CANCELED.value,
            "starts_at": (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat(),
        },
        headers={**headers, "If-Match": initial_etag},
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response = await client.delete(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": activity_id,
        },
        headers={**headers, "If-Match": initial_etag},
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response = await client.delete(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": activity_id,
        },
        headers={**headers, "If-Match": updated_etag},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_activity_missing_if_match_api(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "activity-noifmatch@example.com")
    headers = _auth_header(user.email)
    application_id = await _create_application(async_db_session, user.id)

    response = await client.post(
        "/activities",
        params={"application_id": str(application_id)},
        json={
            "type": ActivityType.OTHER.value,
            "status": ActivityStatus.SCHEDULED.value,
            "starts_at": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        },
        headers=headers,
    )
    activity_id = response.json()["id"]
    etag = response.headers["ETag"]

    response = await client.patch(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": activity_id,
        },
        json={
            "status": ActivityStatus.DONE.value,
            "starts_at": (datetime.now(timezone.utc) + timedelta(hours=7)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response = await client.delete(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": activity_id,
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response = await client.delete(
        "/activities/detail",
        params={
            "application_id": str(application_id),
            "activity_id": activity_id,
        },
        headers={**headers, "If-Match": etag},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
