from __future__ import annotations

from celery import Celery

from src.core.config import settings

celery_app = Celery("job_tracker")

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    beat_schedule={
        "scan-due-reminders": {
            "task": "src.background.tasks.reminders.scan_due_reminders",
            "schedule": settings.REMINDER_SCAN_INTERVAL_SECONDS,
        }
    },
)

celery_app.autodiscover_tasks(["src.background.tasks"])
