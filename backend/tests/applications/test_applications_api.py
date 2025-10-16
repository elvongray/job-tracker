from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.applications.models import AppStatus
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


@pytest.mark.asyncio
async def test_applications_pagination_and_cursor(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "cursor@example.com")
    headers = _auth_header(user.email)

    for idx in range(3):
        payload = {
            "company": f"Company {idx}",
            "role_title": f"Role {idx}",
            "tags": [f"tag{idx}"],
        }
        response = await client.post("/applications", json=payload, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED

    response = await client.get("/applications", params={"limit": 2}, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["next_cursor"]
    cursor = data["next_cursor"]

    response = await client.get(
        "/applications",
        params={"limit": 2, "cursor": cursor},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["next_cursor"] is None


@pytest.mark.asyncio
async def test_applications_filters(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "filters-api@example.com")
    headers = _auth_header(user.email)

    await client.post(
        "/applications",
        json={
            "company": "Acme Corp",
            "role_title": "Backend Engineer",
            "status": AppStatus.SCREENING.value,
            "tags": ["python", "backend"],
        },
        headers=headers,
    )
    await client.post(
        "/applications",
        json={
            "company": "Zenith Labs",
            "role_title": "Frontend Engineer",
            "tags": ["frontend"],
            "archived_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )

    response = await client.get(
        "/applications",
        params={"status": AppStatus.SCREENING.value},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["company"] == "Acme Corp"

    response = await client.get(
        "/applications",
        params={"tag": "python"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert "python" in data["items"][0]["tags"]


@pytest.mark.asyncio
async def test_applications_optimistic_concurrency(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "optimistic@example.com")
    headers = _auth_header(user.email)

    payload = {"company": "FutureTech", "role_title": "Data Scientist"}
    response = await client.post("/applications", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    app_id = response.json()["id"]
    initial_etag = response.headers["ETag"]

    update_payload = {"status": AppStatus.SCREENING.value}
    response = await client.patch(
        f"/applications/{app_id}",
        json=update_payload,
        headers={**headers, "If-Match": initial_etag},
    )
    assert response.status_code == status.HTTP_200_OK
    updated_etag = response.headers["ETag"]
    assert updated_etag != initial_etag

    response = await client.patch(
        f"/applications/{app_id}",
        json={"status": AppStatus.INTERVIEW_LOOP.value},
        headers={**headers, "If-Match": initial_etag},
    )
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_applications_create_get_delete_flow(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "crud@example.com")
    headers = _auth_header(user.email)

    custom_id = uuid4()
    payload = {
        "id": str(custom_id),
        "company": "CreateTest",
        "role_title": "QA Engineer",
    }
    response = await client.post("/applications", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    etag = response.headers["ETag"]

    response = await client.get(f"/applications/{custom_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["company"] == "CreateTest"

    response = await client.delete(
        f"/applications/{custom_id}", headers={**headers, "If-Match": etag}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await client.get(f"/applications/{custom_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_applications_invalid_cursor_error(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "badcursor@example.com")
    headers = _auth_header(user.email)

    response = await client.get(
        "/applications",
        params={"cursor": "not-a-valid-cursor"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body["title"] == "Invalid Request"


@pytest.mark.asyncio
async def test_applications_missing_if_match_header(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "missing-if-match@example.com")
    headers = _auth_header(user.email)

    response = await client.post(
        "/applications",
        json={"company": "NoHeader", "role_title": "Tester"},
        headers=headers,
    )
    etag = response.headers["ETag"]
    app_id = response.json()["id"]

    response = await client.patch(
        f"/applications/{app_id}",
        json={"status": AppStatus.SCREENING.value},
        headers=headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response = await client.delete(f"/applications/{app_id}", headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response = await client.delete(
        f"/applications/{app_id}", headers={**headers, "If-Match": etag}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_applications_delete_version_conflict(
    client: AsyncClient, async_db_session: AsyncSession
):
    user = await _create_user(async_db_session, "delete-conflict-api@example.com")
    headers = _auth_header(user.email)

    response = await client.post(
        "/applications",
        json={"company": "Conflict", "role_title": "Engineer"},
        headers=headers,
    )
    app_id = response.json()["id"]
    etag = response.headers["ETag"]

    response = await client.patch(
        f"/applications/{app_id}",
        json={"status": AppStatus.SCREENING.value},
        headers={**headers, "If-Match": etag},
    )
    assert response.status_code == status.HTTP_200_OK
    new_etag = response.headers["ETag"]

    response = await client.delete(
        f"/applications/{app_id}", headers={**headers, "If-Match": etag}
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response = await client.delete(
        f"/applications/{app_id}", headers={**headers, "If-Match": new_etag}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
