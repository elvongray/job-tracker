"""Background jobs and Celery application."""

from .celery_app import celery_app
from .tasks import email as _email_tasks  # noqa: F401

# Import task modules so Celery discovers them
from .tasks import reminders as _reminder_tasks  # noqa: F401

__all__ = ["celery_app"]
