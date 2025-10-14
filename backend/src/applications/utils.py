from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from src.applications.models import Application
from src.core.exceptions import InvalidRequestError


def encode_cursor(application: Application) -> str:
    payload = {
        "created_at": application.created_at.isoformat(),
        "id": application.id.hex,
    }
    raw = json.dumps(payload).encode("utf-8")
    token = base64.urlsafe_b64encode(raw).decode("utf-8")
    return token.rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + padding).decode("utf-8")
        payload = json.loads(raw)
        created_at = datetime.fromisoformat(payload["created_at"])
        application_id = UUID(payload["id"])
        return created_at, application_id
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise InvalidRequestError("Invalid cursor value.") from exc


def parse_if_match(version: str | None) -> int:
    if not version:
        raise InvalidRequestError("If-Match header is required.")
    candidate = version.strip()
    if candidate.startswith("W/"):
        candidate = candidate[2:].strip()
    candidate = candidate.strip('"')
    try:
        parsed = int(candidate)
    except ValueError as exc:
        raise InvalidRequestError("If-Match header is invalid.") from exc
    if parsed < 0:
        raise InvalidRequestError("If-Match header must be a positive integer.")
    return parsed
