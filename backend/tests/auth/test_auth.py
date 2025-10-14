import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service, utils
from src.core.config import settings as auth_settings
from src.user import models


@pytest.mark.asyncio
async def test_signup_user(client: AsyncClient, async_db_session: AsyncSession):
    """Test user signup and token generation."""
    user_data = {"email": "test@example.com", "password": "securepassword"}

    # Hit the API
    response = await client.post("/auth/signup", json=user_data)
    assert response.status_code == 201

    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Verify the token
    decoded_token = jwt.decode(
        token_data["access_token"],
        auth_settings.JWT_SECRET_KEY,
        algorithms=[auth_settings.JWT_ALGORITHM],
    )
    assert decoded_token["sub"] == user_data["email"]

    # Fresh session for verification
    db_user = await service.get_user_by_email(async_db_session, user_data["email"])
    assert db_user is not None
    assert db_user.email == user_data["email"]


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, async_db_session: AsyncSession):
    user_data = {"email": "login_test@example.com", "password": "password123"}
    hashed_password = utils.get_password_hash(user_data["password"])

    # Add the user to the session
    user = models.User(email=user_data["email"], password=hashed_password)
    async_db_session.add(user)

    # Flush to make the user available in this transaction
    await async_db_session.flush()

    # --- Act: Try to log in via the API ---
    login_data = {"email": user_data["email"], "password": user_data["password"]}
    response = await client.post("/auth/login", json=login_data)

    # --- Assert: Check the response ---
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data.get("token_type") == "bearer"


@pytest.mark.asyncio
async def test_login_user_incorrect_password(
    client: AsyncClient, async_db_session: AsyncSession
):
    """Test login with an incorrect password."""
    user_data = {"email": "wrongpass@example.com", "password": "correctpassword"}
    hashed_password = utils.get_password_hash(user_data["password"])

    # Add the user to the session
    user = models.User(email=user_data["email"], password=hashed_password)
    async_db_session.add(user)

    # Flush to make the user available in this transaction
    await async_db_session.flush()

    # Try to log in with wrong password
    response = await client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
