from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import status

default_exception_message = "Something went wrong. We're looking into it."

ERROR_NAMESPACE = "https://errors.jobtracker.app"


def problem_type(slug: str) -> str:
    return f"{ERROR_NAMESPACE}/{slug}"


class ApplicationError(Exception):
    def __init__(
        self,
        *args: Any,
        detail: str = "We could not process the request.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        title: str = "Application Error",
        error_type: str | None = None,
        meta: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        self.detail = detail
        self.status_code = status_code
        self.title = title
        self.error_type = error_type or problem_type("application-error")
        self.meta = dict(meta or {})
        self.headers = dict(headers or {})
        super().__init__(*args, detail, status_code)


class NotFoundError(ApplicationError):
    def __init__(
        self,
        *args: Any,
        detail: str = "Requested resource was not found.",
        meta: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__(
            *args,
            detail,
            status_code=status.HTTP_404_NOT_FOUND,
            title="Resource Not Found",
            error_type=problem_type("not-found"),
            meta=meta,
            headers=headers,
        )


class InvalidRequestError(ApplicationError):
    def __init__(
        self,
        *args: Any,
        detail: str = "Invalid request.",
        meta: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__(
            *args,
            detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Invalid Request",
            error_type=problem_type("invalid-request"),
            meta=meta,
            headers=headers,
        )


class InvalidToken(ApplicationError):
    def __init__(
        self,
        *args: Any,
        detail: str = "Invalid authentication token",
        meta: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__(
            *args,
            detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Invalid Token",
            error_type=problem_type("invalid-token"),
            meta=meta,
            headers=headers,
        )


class ForbiddenError(ApplicationError):
    def __init__(
        self,
        *args: Any,
        detail: str = "Forbidden",
        meta: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__(
            *args,
            detail,
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            error_type=problem_type("forbidden"),
            meta=meta,
            headers=headers,
        )


class UnauthorizedError(ApplicationError):
    def __init__(
        self,
        *args: Any,
        detail: str = "Unauthorized",
        meta: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__(
            *args,
            detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            error_type=problem_type("unauthorized"),
            meta=meta,
            headers=headers,
        )
