from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_magic_link_flow(client: AsyncClient):
    email = "magic@example.com"

    request_resp = await client.post("/auth/magic-link", json={"email": email})
    assert request_resp.status_code == status.HTTP_202_ACCEPTED
    token = request_resp.json()["token"]

    verify_resp = await client.post("/auth/magic-link/verify", json={"token": token})
    assert verify_resp.status_code == status.HTTP_200_OK
    data = verify_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == status.HTTP_200_OK
    assert me_resp.json()["email"] == email

    reuse_resp = await client.post("/auth/magic-link/verify", json={"token": token})
    assert reuse_resp.status_code == status.HTTP_400_BAD_REQUEST

    logout_resp = await client.post("/auth/logout")
    assert logout_resp.status_code == status.HTTP_204_NO_CONTENT

    me_after_logout = await client.get("/auth/me")
    assert me_after_logout.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_magic_link_invalid_token(client: AsyncClient):
    response = await client.post("/auth/magic-link/verify", json={"token": "invalid"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_google_oauth_placeholder(client: AsyncClient):
    response = await client.get("/auth/google")
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
