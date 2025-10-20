from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from src.auth import schemas, service, utils
from src.auth.dependencies import get_current_user
from src.core.config import settings
from src.db.dependencies import DbSession
from src.user.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_TOKEN_COOKIE_NAME = "access_token"


def _set_access_cookie(response: Response, access_token: str) -> None:
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE.lower(),
        max_age=max_age,
    )


@router.post(
    "/magic-link",
    response_model=schemas.MagicLinkResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_magic_link(
    payload: schemas.MagicLinkRequest,
    db: DbSession,
):
    token, _ = await service.request_magic_link(db, email=payload.email)
    # In production, the token would be emailed. We return it for testing convenience.
    return schemas.MagicLinkResponse(token=token)


@router.post("/magic-link/verify", response_model=schemas.AuthResponse)
async def verify_magic_link(
    payload: schemas.MagicLinkVerifyRequest,
    response: Response,
    db: DbSession,
):
    user = await service.verify_magic_link(db, payload.token)
    access_token = utils.create_access_token(data={"sub": user.email})
    _set_access_cookie(response, access_token)
    return schemas.AuthResponse(access_token=access_token, user=user)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: UserRead = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)


@router.get("/google", include_in_schema=False)
async def google_oauth_placeholder():
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "message": "Google OAuth flow is not implemented in this environment."
        },
    )
