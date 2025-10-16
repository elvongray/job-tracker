from __future__ import annotations

from fastapi import status

from src.core.exceptions import ApplicationError, problem_type


def _auth_error(
    *,
    detail: str,
    status_code: int,
    title: str,
    slug: str,
) -> ApplicationError:
    return ApplicationError(
        detail=detail,
        status_code=status_code,
        title=title,
        error_type=problem_type(f"auth/{slug}"),
    )


CREDENTIALS_EXCEPTION = _auth_error(
    detail="Could not validate credentials.",
    status_code=status.HTTP_401_UNAUTHORIZED,
    title="Invalid Credentials",
    slug="invalid-credentials",
)

USER_ALREADY_EXISTS_EXCEPTION = _auth_error(
    detail="A user with this email already exists.",
    status_code=status.HTTP_409_CONFLICT,
    title="User Already Exists",
    slug="user-already-exists",
)

INCORRECT_CREDENTIALS_EXCEPTION = _auth_error(
    detail="Incorrect email or password.",
    status_code=status.HTTP_401_UNAUTHORIZED,
    title="Incorrect Credentials",
    slug="incorrect-credentials",
)
