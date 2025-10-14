from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import exceptions, utils
from src.db.session import db_session
from src.user import service

# This defines the token URL for our OAuth2 scheme.
# The `tokenUrl` points to the endpoint where a client can obtain a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(db_session)
):
    try:
        email = utils.decode_access_token(token)
    except Exception:
        raise exceptions.CREDENTIALS_EXCEPTION

    user = await service.get_user_by_email(db, email=email)
    if user is None:
        raise exceptions.CREDENTIALS_EXCEPTION
    return user
