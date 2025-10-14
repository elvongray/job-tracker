from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

db_connection_string = f"postgresql://{settings.DATABASE_URL}"
async_db_connection_string = f"postgresql+asyncpg://{settings.DATABASE_URL}"


def get_async_db_engine(db_connection_string: str, debug=False) -> AsyncEngine:
    return create_async_engine(
        url=db_connection_string,
        connect_args={"statement_cache_size": 0},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=debug,
    )


def async_session_factory(
    db_connection_string: str = None,
    db_engine: AsyncEngine = None,
    debug: bool = False,
) -> async_sessionmaker[AsyncSession]:
    if not db_engine and not db_connection_string:
        raise ValueError("Either db_connection_string or db_engine must be provided")
    engine = db_engine or get_async_db_engine(db_connection_string, debug)
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


@asynccontextmanager
async def async_db_session_context(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, Any]:
    session = session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    else:
        try:
            await session.commit()
        except PendingRollbackError:
            await session.rollback()
    finally:
        await session.close()


def get_db_session():
    return async_db_session_context(
        async_session_factory(db_connection_string=async_db_connection_string)
    )


async def db_session():
    async with get_db_session() as session:
        yield session
