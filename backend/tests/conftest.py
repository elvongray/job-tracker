from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urlparse

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.activities.models import Activity  # noqa
from src.app import app
from src.applications.models import Application  # noqa
from src.auth.models import VerificationCode  # noqa
from src.core.config import settings
from src.db.base import SchemaBase
from src.db.session import db_session
from src.reminders.models import Reminder  # noqa

# Ensure all models are registered with the metadata before create_all
from src.user.models import User  # noqa


def _parse_database_url() -> dict[str, Any]:
    parsed = urlparse(f"postgresql://{settings.DATABASE_URL}")
    return {
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") or "app",
    }


DB_CONFIG = _parse_database_url()
TEST_DB_NAME = f"{DB_CONFIG['database']}_test"


def _auth_segment() -> str:
    if DB_CONFIG["password"]:
        return f"{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    return DB_CONFIG["user"]


AUTH_SEGMENT = _auth_segment()
HOST_SEGMENT = f"{DB_CONFIG['host']}:{DB_CONFIG['port']}"

ADMIN_DATABASE_URL = f"postgresql+asyncpg://{AUTH_SEGMENT}@{HOST_SEGMENT}/postgres"
TEST_DATABASE_URL = f"postgresql+asyncpg://{AUTH_SEGMENT}@{HOST_SEGMENT}/{TEST_DB_NAME}"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def ensure_test_database() -> None:
    """Create the dedicated test database if it does not already exist and drop it after tests."""
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": TEST_DB_NAME},
        )
        if result.scalar() is None:
            await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))

    yield

    async with admin_engine.connect() as conn:
        await conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :db_name"
            ),
            {"db_name": TEST_DB_NAME},
        )
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))

    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Yield an engine bound to the Postgres test database."""
    engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)

    async with engine.begin() as conn:
        for enum_name in (
            "app_status",
            "priority_level",
            "location_mode",
            "activity_type",
            "activity_status",
            "interview_stage",
            "interview_medium",
            "followup_channel",
            "reminder_channel",
        ):
            await conn.execute(text(f'DROP TYPE IF EXISTS "{enum_name}" CASCADE'))
        await conn.run_sync(SchemaBase.metadata.drop_all)
        await conn.run_sync(SchemaBase.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session per test."""
    session_maker = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_maker() as session:

        async def override_get_db() -> AsyncGenerator[AsyncSession, Any]:
            yield session

        app.dependency_overrides[db_session] = override_get_db
        try:
            yield session
        finally:
            app.dependency_overrides.pop(db_session, None)
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def client(async_db_session) -> AsyncGenerator[AsyncClient, None]:  # noqa: ARG001
    """Provide an AsyncClient for HTTP requests in tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
