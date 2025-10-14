import logging

from sqlalchemy.exc import IntegrityError  # Import specific exception
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import utils
from src.auth.schemas import UserCreate
from src.user import models
from src.user.schemas import User
from src.user.service import get_user_by_email

logger = logging.getLogger(__name__)


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """Creates a new user account."""
    try:
        hashed_password = utils.get_password_hash(user_create.password)
        db_user = models.User(email=user_create.email, password_hash=hashed_password)

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        # INFO: Log successful creation for audit trails
        logger.info(f"Successfully created user with email: {user_create.email}")

        return User.model_validate(db_user)

    except IntegrityError:
        logger.error(
            f"Failed to create user. Email '{user_create.email}' already exists."
        )
        await db.rollback()
        raise

    except Exception as e:
        # EXCEPTION: Log any other unexpected error with a full stack trace
        logger.exception(
            f"An unexpected error occurred while creating user {user_create.email}: {e}"
        )
        await db.rollback()
        raise


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticates a user with email and password."""
    try:
        user = await get_user_by_email(db, email)
        if not user or not user.password_hash:
            logger.warning(f"Failed authentication attempt for email: {email}")
            return None

        if not utils.verify_password(password, user.password_hash):
            # WARNING: Log failed login attempts for security monitoring
            logger.warning(f"Failed authentication attempt for email: {email}")
            return None

        # INFO: Log successful authentication
        logger.info(f"User {email} authenticated successfully.")
        return user

    except Exception as e:
        # EXCEPTION: Log unexpected database or other errors during authentication
        logger.exception(
            f"An unexpected error occurred during authentication for {email}: {e}"
        )
        return None
