from __future__ import annotations

import asyncio
import logging

from src.background.celery_app import celery_app
from src.background.reminder_engine import process_due_reminders
from src.db.session import (
    async_db_connection_string,
    async_db_session_context,
    async_session_factory,
)

logger = logging.getLogger(__name__)

_session_factory = async_session_factory(
    db_connection_string=async_db_connection_string
)


@celery_app.task(
    name="src.background.tasks.reminders.scan_due_reminders", ignore_result=True
)
def scan_due_reminders() -> None:
    """Entry-point task for scanning and dispatching due reminders."""
    logger.debug("Starting reminder scan task")
    asyncio.run(_run_scan())


async def _run_scan() -> None:
    async with async_db_session_context(_session_factory) as session:
        await process_due_reminders(session)
