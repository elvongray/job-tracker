import pytest
from fastapi import status

from src.app import app
from src.core.exceptions import (
    InvalidRequestError,
    default_exception_message,
    problem_type,
)


@app.get("/tests/error-handling/invalid")  # pragma: no cover - exercised via tests
async def _raise_invalid_request():
    raise InvalidRequestError(
        detail="Company field is required.",
        meta={"field": "company"},
    )


@app.get("/tests/error-handling/unexpected")  # pragma: no cover - exercised via tests
async def _raise_unexpected():
    raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_application_error_returns_problem_details(client):
    response = await client.get("/tests/error-handling/invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    payload = response.json()

    assert payload["type"] == problem_type("invalid-request")
    assert payload["title"] == "Invalid Request"
    assert payload["status"] == status.HTTP_400_BAD_REQUEST
    assert payload["detail"] == "Company field is required."
    assert payload["instance"].startswith("req_")
    assert payload["meta"]["path"] == "/tests/error-handling/invalid"
    assert payload["meta"]["method"] == "GET"
    assert payload["meta"]["field"] == "company"


@pytest.mark.asyncio
async def test_unexpected_exception_returns_problem_details(client):
    response = await client.get("/tests/error-handling/unexpected")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    payload = response.json()

    assert payload["type"] == problem_type("internal-error")
    assert payload["title"] == "Unexpected Error"
    assert payload["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert payload["detail"] == default_exception_message
    assert payload["instance"].startswith("req_")
    assert payload["meta"]["path"] == "/tests/error-handling/unexpected"
    assert payload["meta"]["method"] == "GET"
