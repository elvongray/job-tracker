from __future__ import annotations

import asyncio
import logging

from src.background.celery_app import celery_app
from src.background.reminder_engine import process_due_reminders
from src.db.session import get_db_session

logger = logging.getLogger(__name__)


@celery_app.task(
    name="src.background.tasks.reminders.scan_due_reminders", ignore_result=True
)
def scan_due_reminders() -> None:
    """Entry-point task for scanning and dispatching due reminders."""
    logger.debug("Starting reminder scan task")
    asyncio.run(_run_scan())


async def _run_scan() -> None:
    async with get_db_session() as session:
        await process_due_reminders(session)
