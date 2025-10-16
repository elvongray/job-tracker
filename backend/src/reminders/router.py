from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from src.auth.dependencies import get_current_user
from src.core.exceptions import NotFoundError
from src.db.dependencies import DbSession
from src.reminders import schemas, service
from src.user.schemas import UserRead

router = APIRouter(prefix="/reminders", tags=["Reminders"])


def _set_etag(response: Response, version: int) -> None:
    response.headers["ETag"] = f'W/"{version}"'


@router.get("", response_model=list[schemas.ReminderOut])
async def list_reminders(
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    due_before: datetime | None = Query(default=None),
    due_after: datetime | None = Query(default=None),
    sent: bool | None = Query(default=None),
):
    reminders = await service.list_reminders(
        db,
        user_id=current_user.id,
        due_before=due_before,
        due_after=due_after,
        sent=sent,
    )
    return [schemas.ReminderOut.model_validate(reminder) for reminder in reminders]


@router.post(
    "", response_model=schemas.ReminderOut, status_code=status.HTTP_201_CREATED
)
async def create_reminder(
    response: Response,
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    payload: schemas.ReminderCreate,
):
    data = payload.model_dump(exclude_none=True)
    reminder = await service.create_reminder(
        db,
        user_id=current_user.id,
        data=data,
    )
    dto = schemas.ReminderOut.model_validate(reminder)
    _set_etag(response, dto.version)
    return dto


@router.get("/detail", response_model=schemas.ReminderOut)
async def get_reminder(
    response: Response,
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    reminder_id: UUID = Query(...),
):
    reminder = await service.get_reminder(
        db,
        user_id=current_user.id,
        reminder_id=reminder_id,
    )
    dto = schemas.ReminderOut.model_validate(reminder)
    _set_etag(response, dto.version)
    return dto


@router.patch("/detail", response_model=schemas.ReminderOut)
async def update_reminder(
    response: Response,
    db: DbSession,
    payload: schemas.ReminderUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    reminder_id: UUID = Query(...),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    update_data = payload.model_dump(exclude_unset=True)
    reminder = await service.update_reminder(
        db,
        user_id=current_user.id,
        reminder_id=reminder_id,
        update_data=update_data,
        if_match=if_match,
    )
    dto = schemas.ReminderOut.model_validate(reminder)
    _set_etag(response, dto.version)
    return dto


@router.delete("/detail", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    db: DbSession,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    reminder_id: UUID = Query(...),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    reminder = await service.get_reminder(
        db,
        user_id=current_user.id,
        reminder_id=reminder_id,
    )
    if reminder.id != reminder_id:
        raise NotFoundError(
            "Reminder not found for this application.",
            meta={
                "resource": "activities",
                "reminder_id": str(reminder_id),
            },
        )

    await service.delete_reminder(
        db,
        user_id=current_user.id,
        reminder_id=reminder_id,
        if_match=if_match,
    )
