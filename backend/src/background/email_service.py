from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from src.core.config import settings

_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_TLS,
    MAIL_SSL_TLS=settings.MAIL_SSL,
    TEMPLATE_FOLDER=Path(settings.MAIL_TEMPLATE_DIR),
    USE_CREDENTIALS=bool(settings.MAIL_USERNAME and settings.MAIL_PASSWORD),
)

_mail_client = FastMail(_config)


async def send_reminder_email(
    *,
    recipients: Iterable[str],
    subject: str,
    template_name: str,
    template_body: dict[str, object],
) -> None:
    message = MessageSchema(
        subject=subject,
        recipients=list(recipients),
        template_body={**template_body, "sent_at": datetime.utcnow().isoformat()},
        subtype="html",
    )
    await _mail_client.send_message(message, template_name=template_name)
