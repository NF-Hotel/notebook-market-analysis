from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config import Settings
from app.infrastructure.main import build_app

KEY = {"X-API-Key": "secret"}


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        _env_file=None,
        data_source="csv",
        api_token="secret",
        output_directory=tmp_path,
    )
    return TestClient(build_app(settings))


def test_health_needs_no_key(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
def test_holidays_need_the_key(client: TestClient, headers: dict[str, str]) -> None:
    assert client.get("/api/v1/holidays", headers=headers).status_code == 401
    assert client.post("/api/v1/holidays/update", headers=headers).status_code == 401


def test_without_a_configured_token_everything_but_health_is_refused(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, data_source="csv", output_directory=tmp_path)
    client = TestClient(build_app(settings))
    assert client.get("/api/v1/holidays", headers=KEY).status_code == 401


def test_get_returns_the_contract_shape(client: TestClient) -> None:
    body = client.get("/api/v1/holidays", params={"year": 2025}, headers=KEY).json()
    assert body["country"] == "DK"
    assert (body["first_year"], body["last_year"]) == (2025, 2025)
    assert {"name": "Good Friday", "start_date": "2025-04-18", "end_date": "2025-04-18"} in body[
        "holidays"
    ]


def test_update_then_get(client: TestClient) -> None:
    updated = client.post(
        "/api/v1/holidays/update", params={"first_year": 2030, "last_year": 2031}, headers=KEY
    ).json()
    assert (updated["first_year"], updated["last_year"]) == (2030, 2031)
    stored = client.get("/api/v1/holidays", headers=KEY).json()
    assert stored == updated


def test_reversed_years_are_a_bad_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/holidays/update", params={"first_year": 2031, "last_year": 2030}, headers=KEY
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_non_numeric_year_is_unprocessable(client: TestClient) -> None:
    assert client.get("/api/v1/holidays?year=abc", headers=KEY).status_code == 422
