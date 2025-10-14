from fastapi import status

from src.core.exceptions import ApplicationError

CREDENTIALS_EXCEPTION = ApplicationError(
    status_code=status.HTTP_401_UNAUTHORIZED,
    msg="Could not validate credentials",
)

USER_ALREADY_EXISTS_EXCEPTION = ApplicationError(
    status_code=status.HTTP_409_CONFLICT,
    msg="User with this email already exists",
)

INCORRECT_CREDENTIALS_EXCEPTION = ApplicationError(
    status_code=status.HTTP_401_UNAUTHORIZED,
    msg="Incorrect email or password",
)
