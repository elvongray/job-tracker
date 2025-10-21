from __future__ import annotations

import asyncio

from src.background.celery_app import celery_app
from src.background.email_service import send_reminder_email


@celery_app.task(
    name="src.background.tasks.email.send_reminder_email",
    ignore_result=True,
)
def send_email_task(
    recipients: list[str],
    subject: str,
    template_name: str,
    template_body: dict,
) -> None:
    """Wrapper to send reminder emails asynchronously."""
    asyncio.run(
        send_reminder_email(
            recipients=recipients,
            subject=subject,
            template_name=template_name,
            template_body=template_body,
        )
    )
