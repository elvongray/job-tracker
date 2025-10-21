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
    "/verification-code",
    response_model=schemas.VerificationCodeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_verification_code(
    payload: schemas.VerificationCodeRequest,
    db: DbSession,
):
    code, _ = await service.request_verification_code(db, email=payload.email)
    # In production, the code would be emailed or sent via SMS. Return for tests.
    return schemas.VerificationCodeResponse(code=code)


@router.post("/verification-code/verify", response_model=schemas.AuthResponse)
async def verify_verification_code(
    payload: schemas.VerificationCodeVerifyRequest,
    response: Response,
    db: DbSession,
):
    user = await service.verify_verification_code(db, payload.code)
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
