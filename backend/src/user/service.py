from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User as UserModel
from src.user.schemas import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Retrieves a user by their email address."""
    query = select(UserModel).where(UserModel.email == email)
    result = (await db.scalars(query)).one_or_none()
    return User.model_validate(result) if result else None
