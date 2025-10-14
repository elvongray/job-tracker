from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from src.applications import schemas, service
from src.applications.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.applications.models import AppStatus, PriorityLevel
from src.auth.dependencies import get_current_user
from src.db.dependencies import DbSession
from src.user.schemas import UserRead

router = APIRouter(prefix="/applications", tags=["Applications"])


def _set_etag(response: Response, version: int) -> None:
    response.headers["ETag"] = f'W/"{version}"'


@router.get("/", response_model=schemas.ApplicationListResponse)
async def list_applications(
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    cursor: str | None = Query(default=None, description="Opaque pagination cursor."),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    status_filter: AppStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    priority: PriorityLevel | None = Query(default=None),
    archived: bool | None = Query(default=None),
):
    applications, next_cursor = await service.list_applications(
        db,
        user_id=current_user.id,
        limit=limit,
        cursor=cursor,
        status_filter=status_filter,
        q=q,
        tag=tag,
        priority=priority,
        archived=archived,
    )
    items = [schemas.ApplicationOut.model_validate(app) for app in applications]
    return schemas.ApplicationListResponse(items=items, next_cursor=next_cursor)


@router.post(
    "/", response_model=schemas.ApplicationOut, status_code=status.HTTP_201_CREATED
)
async def create_application(
    response: Response,
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    payload: schemas.ApplicationCreate,
):
    data = payload.model_dump(exclude_none=True)
    application = await service.create_application(
        db,
        user_id=current_user.id,
        data=data,
    )
    dto = schemas.ApplicationOut.model_validate(application)
    _set_etag(response, dto.version)
    return dto


@router.get("/{application_id}", response_model=schemas.ApplicationOut)
async def get_application(
    response: Response,
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID,
):
    application = await service.get_application(
        db,
        user_id=current_user.id,
        application_id=application_id,
    )
    dto = schemas.ApplicationOut.model_validate(application)
    _set_etag(response, dto.version)
    return dto


@router.patch("/{application_id}", response_model=schemas.ApplicationOut)
async def update_application(
    response: Response,
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID,
    payload: schemas.ApplicationUpdate,
    if_match: Annotated[str | None, Header(default=None, alias="If-Match")] = None,
):
    update_data = payload.model_dump(exclude_unset=True)
    application = await service.update_application(
        db,
        user_id=current_user.id,
        application_id=application_id,
        update_data=update_data,
        if_match=if_match,
    )
    dto = schemas.ApplicationOut.model_validate(application)
    _set_etag(response, dto.version)
    return dto


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID,
    if_match: Annotated[str | None, Header(default=None, alias="If-Match")] = None,
):
    await service.delete_application(
        db,
        user_id=current_user.id,
        application_id=application_id,
        if_match=if_match,
    )
