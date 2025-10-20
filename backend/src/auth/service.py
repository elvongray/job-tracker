from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import MagicLinkToken
from src.core.config import settings
from src.core.exceptions import InvalidRequestError
from src.user.models import User as UserModel
from src.user.schemas import UserRead

logger = logging.getLogger(__name__)


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


async def request_magic_link(db: AsyncSession, email: str) -> tuple[str, UserRead]:
    """Ensure a user exists for the email and create a magic link token."""
    query = (
        select(UserModel)
        .where(UserModel.email == email)
        .options(selectinload(UserModel.settings))
    )
    user = (await db.scalars(query)).one_or_none()
    if not user:
        user = UserModel(email=email)
        db.add(user)
        await db.flush()
        logger.info("Created new user via magic link", extra={"email": email})

    token_value = _generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.MAGIC_LINK_TOKEN_EXPIRE_MINUTES
    )
    token = MagicLinkToken(user_id=user.id, token=token_value, expires_at=expires_at)
    db.add(token)
    await db.commit()

    refreshed_user = (
        await db.scalars(
            select(UserModel)
            .where(UserModel.id == user.id)
            .options(selectinload(UserModel.settings))
        )
    ).one()
    return token_value, UserRead.model_validate(refreshed_user)


async def verify_magic_link(db: AsyncSession, token_value: str) -> UserRead:
    """Validate a magic link token and return the associated user."""
    query = (
        select(MagicLinkToken)
        .where(MagicLinkToken.token == token_value)
        .options(selectinload(MagicLinkToken.user).selectinload(UserModel.settings))
    )
    token = (await db.scalars(query)).one_or_none()
    now = datetime.now(timezone.utc)
    if not token:
        logger.warning("Magic link token not found", extra={"token": token_value})
        raise InvalidRequestError("Invalid or expired token.")
    if token.used_at is not None:
        logger.warning(
            "Magic link token already used",
            extra={"token_id": str(token.id)},
        )
        raise InvalidRequestError("Token has already been used.")
    if token.expires_at < now:
        logger.warning(
            "Magic link token expired",
            extra={"token_id": str(token.id)},
        )
        raise InvalidRequestError("Token has expired.")

    await db.execute(
        update(MagicLinkToken).where(MagicLinkToken.id == token.id).values(used_at=now)
    )
    await db.commit()
    user = token.user
    if not user:
        raise InvalidRequestError("Token is not associated with a user.")
    return UserRead.model_validate(user)
