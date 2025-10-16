from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.user.models import User as UserModel
from src.user.schemas import UserRead


async def get_user_by_email(db: AsyncSession, email: str) -> UserRead | None:
    """Retrieve a user by email with settings eagerly loaded for safe validation."""
    query = (
        select(UserModel)
        .where(UserModel.email == email)
        .options(selectinload(UserModel.settings))
    )
    result = (await db.scalars(query)).one_or_none()
    return UserRead.model_validate(result) if result else None
