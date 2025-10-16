from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from src.activities import schemas, service
from src.auth.dependencies import get_current_user
from src.core.exceptions import NotFoundError
from src.db.dependencies import DbSession
from src.user.schemas import UserRead

router = APIRouter(prefix="/activities", tags=["Activities"])


def _set_etag(response: Response, version: int) -> None:
    response.headers["ETag"] = f'W/"{version}"'


@router.get("", response_model=list[schemas.ActivityOut])
async def list_activities(
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID = Query(..., description="Parent application identifier."),
):
    activities = await service.list_activities_for_application(
        db,
        user_id=current_user.id,
        application_id=application_id,
    )
    return [schemas.ActivityOut.model_validate(activity) for activity in activities]


@router.post(
    "", response_model=schemas.ActivityOut, status_code=status.HTTP_201_CREATED
)
async def create_activity(
    response: Response,
    db: DbSession,
    payload: schemas.ActivityCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID = Query(..., description="Parent application identifier."),
):
    data = payload.model_dump(exclude_none=True)
    activity = await service.create_activity(
        db,
        user_id=current_user.id,
        application_id=application_id,
        data=data,
    )
    dto = schemas.ActivityOut.model_validate(activity)
    _set_etag(response, dto.version)
    return dto


@router.get("/detail", response_model=schemas.ActivityOut)
async def get_activity(
    response: Response,
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID = Query(..., description="Parent application identifier."),
    activity_id: UUID = Query(..., description="Activity identifier."),
):
    activity = await service.get_activity(
        db,
        user_id=current_user.id,
        activity_id=activity_id,
    )
    if activity.application_id != application_id:
        raise NotFoundError(
            "Activity not found for this application.",
            meta={
                "resource": "activities",
                "application_id": str(application_id),
                "activity_id": str(activity_id),
            },
        )
    dto = schemas.ActivityOut.model_validate(activity)
    _set_etag(response, dto.version)
    return dto


@router.patch("/detail", response_model=schemas.ActivityOut)
async def update_activity(
    response: Response,
    db: DbSession,
    payload: schemas.ActivityUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID = Query(..., description="Parent application identifier."),
    activity_id: UUID = Query(..., description="Activity identifier."),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    update_data = payload.model_dump(exclude_unset=True)
    activity = await service.update_activity(
        db,
        user_id=current_user.id,
        activity_id=activity_id,
        update_data=update_data,
        if_match=if_match,
    )
    if activity.application_id != application_id:
        raise NotFoundError(
            "Activity not found for this application.",
            meta={
                "resource": "activities",
                "application_id": str(application_id),
                "activity_id": str(activity_id),
            },
        )
    dto = schemas.ActivityOut.model_validate(activity)
    _set_etag(response, dto.version)
    return dto


@router.delete("/detail", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    application_id: UUID = Query(..., description="Parent application identifier."),
    activity_id: UUID = Query(..., description="Activity identifier."),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    activity = await service.get_activity(
        db,
        user_id=current_user.id,
        activity_id=activity_id,
        eager=False,
    )
    if activity.application_id != application_id:
        raise NotFoundError(
            "Activity not found for this application.",
            meta={
                "resource": "activities",
                "application_id": str(application_id),
                "activity_id": str(activity_id),
            },
        )
    await service.delete_activity(
        db,
        user_id=current_user.id,
        activity_id=activity_id,
        if_match=if_match,
    )
