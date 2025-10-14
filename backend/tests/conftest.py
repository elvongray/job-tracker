from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app import app
from src.core.config import settings
from src.db.base import SchemaBase
from src.db.session import db_session

# This overrides the database URL for testing
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.DATABASE_URL}_test"
ADMIN_DATABASE_URL = "postgresql+asyncpg://app:app@localhost:5432/postgres"


@pytest_asyncio.fixture(scope="session")
async def setup_test_database():
    """Set up the test database once per session."""
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")

    try:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname='app_test'")
            )
            if result.scalar() is None:
                await conn.execute(text("CREATE DATABASE app_test;"))
    finally:
        await admin_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a fresh engine for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SchemaBase.metadata.drop_all)
        await conn.run_sync(SchemaBase.metadata.create_all)

    yield engine

    # Clean shutdown
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session that's isolated per test.
    """
    SessionMaker = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, class_=AsyncSession
    )

    async with SessionMaker() as session:
        # Override the app's database dependency
        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield session

        app.dependency_overrides[db_session] = override_get_db

        try:
            yield session
        finally:
            # Always clean up
            app.dependency_overrides.clear()
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an AsyncClient for making HTTP requests in tests.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
