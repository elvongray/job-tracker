from fastapi import Cookie, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import exceptions, utils
from src.db.session import db_session
from src.user import service


def _extract_token(
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return access_token


async def get_current_user(
    token: str | None = Depends(_extract_token),
    db: AsyncSession = Depends(db_session),
):
    if not token:
        raise exceptions.CREDENTIALS_EXCEPTION
    try:
        email = utils.decode_access_token(token)
    except Exception:
        raise exceptions.CREDENTIALS_EXCEPTION

    user = await service.get_user_by_email(db, email=email)
    if user is None:
        raise exceptions.CREDENTIALS_EXCEPTION
    return user
