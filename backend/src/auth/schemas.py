from __future__ import annotations

from pydantic import BaseModel, EmailStr

from src.user.schemas import UserRead


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    message: str = "Magic link sent"
    token: str


class MagicLinkVerifyRequest(BaseModel):
    token: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(Token):
    user: UserRead


class TokenData(BaseModel):
    email: str | None = None
