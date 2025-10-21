from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from src.background.tasks.email import send_email_task
from src.core.config import settings
from src.reminders import service as reminder_service
from src.reminders.models import Reminder, ReminderChannel
from src.user.models import User


@dataclass(slots=True)
class ReminderProcessingResult:
    sent: int = 0
    deferred: int = 0


async def process_due_reminders(
    session: AsyncSession,
    now: datetime | None = None,
) -> ReminderProcessingResult:
    """Process reminders that are due and dispatch them when appropriate."""
    current_time = now or datetime.now(timezone.utc)
    reminders = await reminder_service.get_due_reminders(session, now=current_time)
    if settings.REMINDER_DISPATCH_BATCH_SIZE > 0:
        reminders = reminders[: settings.REMINDER_DISPATCH_BATCH_SIZE]

    if not reminders:
        return ReminderProcessingResult()

    sent = 0
    deferred = 0

    for reminder in reminders:
        user = reminder.user
        if not user:
            continue
        defer_until = _next_allowed_send_time(user, current_time)
        if defer_until and defer_until > current_time:
            reminder.due_at = defer_until
            reminder.version += 1
            deferred += 1
            continue

        _dispatch_reminder(reminder, current_time)
        reminder.sent = True
        reminder.sent_at = current_time
        reminder.version += 1
        sent += 1

    await session.commit()
    return ReminderProcessingResult(sent=sent, deferred=deferred)


def _dispatch_reminder(reminder: Reminder, now: datetime) -> None:
    dispatched = [channel.value for channel in _parse_channels(reminder.channels)]
    meta = dict(reminder.meta or {})
    meta["dispatched_channels"] = dispatched
    meta["dispatched_at"] = now.isoformat()

    default_body = (
        f"Reminder: {reminder.title}."
        f" Due at {reminder.due_at.astimezone(timezone.utc).isoformat()}"
    )
    meta_body = meta.get("body") or default_body
    reminder.meta = meta

    if ReminderChannel.EMAIL.value in dispatched and reminder.user:
        recipients = [reminder.user.email]
        send_email_task.delay(
            recipients,
            subject=reminder.title,
            template_name="reminder_email.html",
            template_body={
                "title": reminder.title,
                "body": meta_body,
                "action_url": meta.get("action_url"),
            },
        )


def _parse_channels(
    channels: Iterable[ReminderChannel | str | None],
) -> list[ReminderChannel]:
    parsed: list[ReminderChannel] = []
    for channel in channels or []:
        if channel is None:
            continue
        if isinstance(channel, ReminderChannel):
            parsed.append(channel)
        else:
            try:
                parsed.append(ReminderChannel(channel))
            except ValueError:
                continue
    return parsed or [ReminderChannel.IN_APP]


def _next_allowed_send_time(user: User, now: datetime) -> datetime | None:
    settings = user.settings
    if not settings or not settings.quiet_hours_start or not settings.quiet_hours_end:
        return None

    tz = _resolve_timezone(user.timezone)
    local_now = now.astimezone(tz)
    start = settings.quiet_hours_start
    end = settings.quiet_hours_end

    if start == end:
        return None

    within = _is_within_quiet_hours(local_now.time(), start, end)
    if not within:
        return None

    local_end = datetime.combine(local_now.date(), end, tzinfo=tz)
    if local_end <= local_now:
        local_end += timedelta(days=1)
    return local_end.astimezone(timezone.utc)


def _is_within_quiet_hours(current: time, start: time, end: time) -> bool:
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _resolve_timezone(tz_name: str | None) -> ZoneInfo:
    if not tz_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")
