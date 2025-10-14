from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    ApplicationError,
    default_exception_message,
    problem_type,
)


def add_exception_handlers(app: FastAPI):
    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, _: Exception):
        problem = _build_problem_detail(
            request,
            ApplicationError(
                default_exception_message,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                title="Unexpected Error",
                error_type=problem_type("internal-error"),
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem,
        )

    @app.exception_handler(ApplicationError)
    async def http_exception_handler(request: Request, exc: ApplicationError):
        problem = _build_problem_detail(request, exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=problem,
            headers=exc.headers,
        )


def _ensure_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id
    request_id = f"req_{uuid4().hex}"
    request.state.request_id = request_id
    return request_id


def _build_problem_detail(request: Request, exc: ApplicationError) -> dict[str, object]:
    request_id = _ensure_request_id(request)
    meta = {"method": request.method, "path": request.url.path}
    meta.update(exc.meta)
    return {
        "type": exc.error_type,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": request_id,
        "meta": meta,
    }
