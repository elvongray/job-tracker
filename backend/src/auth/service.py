from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import VerificationCode
from src.background.tasks.email import send_email_task
from src.core.config import settings
from src.core.exceptions import InvalidRequestError
from src.user.models import User as UserModel
from src.user.schemas import UserRead

logger = logging.getLogger(__name__)


def _generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


async def request_verification_code(
    db: AsyncSession, email: str
) -> tuple[str, UserRead]:
    """Ensure a user exists for the email and create a verification code."""
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
        logger.info("Created new user via verification code", extra={"email": email})

    code_value = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES
    )
    verification_code = VerificationCode(
        user_id=user.id, code=code_value, expires_at=expires_at
    )
    db.add(verification_code)
    await db.commit()

    refreshed_user = (
        await db.scalars(
            select(UserModel)
            .where(UserModel.id == user.id)
            .options(selectinload(UserModel.settings))
        )
    ).one()
    user_read = UserRead.model_validate(refreshed_user)

    if user_read.email:
        send_email_task.delay(
            recipients=[user_read.email],
            subject="Your Job Hunt Tracker verification code",
            template_name="verification_code_email.html",
            template_body={
                "code": code_value,
                "expires_in": settings.VERIFICATION_CODE_EXPIRE_MINUTES,
                "email": user_read.email,
            },
        )

    return code_value, user_read


async def verify_verification_code(db: AsyncSession, code_value: str) -> UserRead:
    """Validate a verification code and return the associated user."""
    query = (
        select(VerificationCode)
        .where(VerificationCode.code == code_value)
        .options(selectinload(VerificationCode.user).selectinload(UserModel.settings))
    )
    token = (await db.scalars(query)).one_or_none()
    now = datetime.now(timezone.utc)
    if not token:
        logger.warning("Verification code not found", extra={"code": code_value})
        raise InvalidRequestError("Invalid or expired token.")
    if token.used_at is not None:
        logger.warning(
            "Verification code already used",
            extra={"verification_code_id": str(token.id)},
        )
        raise InvalidRequestError("Token has already been used.")
    if token.expires_at < now:
        logger.warning(
            "Verification code expired",
            extra={"verification_code_id": str(token.id)},
        )
        raise InvalidRequestError("Token has expired.")

    await db.execute(
        update(VerificationCode)
        .where(VerificationCode.id == token.id)
        .values(used_at=now)
    )
    await db.commit()
    user = token.user
    if not user:
        raise InvalidRequestError("Token is not associated with a user.")
    return UserRead.model_validate(user)
