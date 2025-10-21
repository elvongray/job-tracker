from __future__ import annotations

from pydantic import BaseModel, EmailStr

from src.user.schemas import UserRead


class VerificationCodeRequest(BaseModel):
    email: EmailStr


class VerificationCodeResponse(BaseModel):
    message: str = "Verification code sent"
    code: str


class VerificationCodeVerifyRequest(BaseModel):
    code: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(Token):
    user: UserRead


class TokenData(BaseModel):
    email: str | None = None
