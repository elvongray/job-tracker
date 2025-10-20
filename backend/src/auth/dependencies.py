from fastapi import Cookie, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import exceptions, utils
from src.db.session import db_session
from src.user import service

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    bearer_credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_cookie: str | None = Cookie(default=None),
    db: AsyncSession = Depends(db_session),
):
    token = None
    if bearer_credentials:
        token = bearer_credentials.credentials
    elif access_cookie:
        token = access_cookie

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
