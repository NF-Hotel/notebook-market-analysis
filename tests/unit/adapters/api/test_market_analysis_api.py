import json
import random
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.adapters.api.app import create_api
from app.adapters.storage.holiday_file_store import FileHolidayStore
from app.adapters.storage.run_file_store import FileRunStore
from app.application.holidays import HolidayService
from app.application.insights import UnconfiguredInsightProvider
from app.application.ports.insight_provider import InsightProvider
from app.application.runs import ExecuteRun, GetRun, GetRunResult, StartRun
from app.domain.run import Run
from app.infrastructure.config import Settings
from app.infrastructure.main import build_app
from tests.unit.run_fakes import (
    T0,
    ManualTaskRunner,
    RecordingInsightProvider,
    SequentialIds,
    SteppingClock,
    booking_body,
    request_body,
)

KEY = {"X-API-Key": "secret"}
RUNS = "/api/v1/market-analysis/runs"
CONTRACT = Path(__file__).parents[4] / "openapi" / "market-contract.yaml"
UNKNOWN_ID = "00000000-0000-4000-8000-0000000000ff"
BOOKING_COUNT = 55_484
TIME_LIMIT_SECONDS = 60.0


class Service:
    def __init__(self, root: Path, insights: InsightProvider | None = None) -> None:
        self.runner = ManualTaskRunner()
        self.store = FileRunStore(root / "runs")
        clock, ids = SteppingClock(), SequentialIds()
        execute = ExecuteRun(
            self.store,
            HolidayService(FileHolidayStore(root / "holidays.json")),
            insights or UnconfiguredInsightProvider(),
            clock,
            ids,
        )
        app = create_api(
            HolidayService(FileHolidayStore(root / "holidays.json")),
            StartRun(self.store, self.runner, execute, clock, ids),
            GetRun(self.store),
            GetRunResult(self.store),
            "secret",
        )
        self.client = TestClient(app)

    def post(self, body: object, **params: Any) -> Any:  # noqa: ANN401
        return self.client.post(RUNS, content=json.dumps(body), params=params, headers=KEY)

    def get(self, path: str) -> Any:  # noqa: ANN401
        return self.client.get(path, headers=KEY)


@pytest.fixture
def service(tmp_path: Path) -> Service:
    return Service(tmp_path)


def _validator() -> Draft202012Validator:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return Draft202012Validator(
        {"$ref": "#/components/schemas/RunResult", "components": contract["components"]}
    )


def _stored_runs(service: Service) -> list[Path]:
    root = service.store._root
    return list(root.glob("*")) if root.exists() else []


def test_start_returns_202_at_once_with_the_run_id_and_state_queued(service: Service) -> None:
    response = service.post(request_body())
    assert response.status_code == 202
    body = response.json()
    assert body["state"] == "queued"
    assert body["run_id"]
    assert "created_at" in body
    assert len(service.runner.tasks) == 1


def test_the_state_follows_queued_running_completed(tmp_path: Path) -> None:
    provider = RecordingInsightProvider()
    service = Service(tmp_path, provider)
    states = []
    run_id = service.post(request_body()).json()["run_id"]
    states.append(service.get(f"{RUNS}/{run_id}").json()["state"])
    provider.on_call = lambda: states.append(service.get(f"{RUNS}/{run_id}").json()["state"])
    service.runner.run_all()
    final = service.get(f"{RUNS}/{run_id}").json()
    assert states[0] == "queued"
    assert set(states[1:]) == {"running"}
    assert final["state"] == "completed"
    assert {"created_at", "started_at", "finished_at"} <= set(final)
    assert "error_code" not in final


def test_the_result_of_a_completed_run_is_schema_1_1_and_valid(service: Service) -> None:
    run_id = service.post(request_body()).json()["run_id"]
    service.runner.run_all()
    response = service.get(f"{RUNS}/{run_id}/result")
    assert response.status_code == 200
    result = response.json()
    assert result["schema_version"] == "1.1"
    assert len(result["analyses"]) == 9
    _validator().validate(result)


def test_the_run_is_kept_in_a_folder_with_state_and_result(service: Service) -> None:
    run_id = service.post(request_body()).json()["run_id"]
    service.runner.run_all()
    folder = service.store._root / run_id
    assert (folder / "state.json").is_file()
    assert (folder / "result.json").is_file()


def test_a_second_start_while_a_run_is_active_is_refused_with_run_active(
    service: Service,
) -> None:
    service.post(request_body())
    response = service.post(request_body())
    assert response.status_code == 409
    assert response.json()["code"] == "run_active"
    assert len(_stored_runs(service)) == 1


def test_a_new_start_is_accepted_after_the_run_finished(service: Service) -> None:
    service.post(request_body())
    service.runner.run_all()
    assert service.post(request_body()).status_code == 202


@pytest.mark.parametrize(
    "body",
    [
        request_body(bookings=[]),
        request_body(room_count=0),
        {"bookings": [booking_body()]},
        request_body(period={"first_date": "2024-02-01", "last_date": "2024-01-01"}),
        request_body(bookings=[booking_body(is_canceled="no")]),
        request_body(bookings=[booking_body(unknown_field=1)]),
        request_body(bookings=[booking_body(stays_in_week_nights=-1)]),
        request_body(bookings=[booking_body(arrival_date="not a date")]),
        request_body(bookings=[{k: v for k, v in booking_body().items() if k != "country"}]),
        request_body(room_count=1.5),
        {**request_body(), "extra": True},
    ],
    ids=[
        "empty-list",
        "no-rooms",
        "room-count-missing",
        "period-reversed",
        "wrong-type",
        "unknown-field",
        "negative-nights",
        "bad-date",
        "no-country",
        "fractional-rooms",
        "unknown-request-field",
    ],
)
def test_an_invalid_body_is_400_invalid_request_and_nothing_is_stored(
    service: Service, body: dict[str, Any]
) -> None:
    response = service.post(body)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert _stored_runs(service) == []
    assert service.runner.tasks == []


def test_a_body_that_is_not_json_is_400(service: Service) -> None:
    response = service.client.post(RUNS, content=b"{nope", headers=KEY)
    assert (response.status_code, response.json()["code"]) == (400, "invalid_request")


def test_an_invalid_insights_parameter_is_400(service: Service) -> None:
    response = service.post(request_body(), insights="maybe")
    assert (response.status_code, response.json()["code"]) == (400, "invalid_request")


def test_the_error_message_does_not_repeat_the_values_sent(service: Service) -> None:
    response = service.post(request_body(bookings=[booking_body(hotel=5, country="SECRETVALUE")]))
    assert "SECRETVALUE" not in response.text


def test_a_booking_with_a_price_as_integer_or_decimal_is_valid(service: Service) -> None:
    bookings = [booking_body(1, price_per_night=100), booking_body(2, price_per_night=99.5)]
    assert service.post(request_body(bookings=bookings)).status_code == 202


def test_insights_false_gives_no_insight_key(service: Service) -> None:
    run_id = service.post(request_body(), insights="false").json()["run_id"]
    service.runner.run_all()
    result = service.get(f"{RUNS}/{run_id}/result").json()
    assert all("insight" not in a for a in result["analyses"].values())
    assert result["insights"]["requested"] is False


def test_insights_default_true_without_a_provider_is_unavailable(service: Service) -> None:
    run_id = service.post(request_body()).json()["run_id"]
    service.runner.run_all()
    result = service.get(f"{RUNS}/{run_id}/result").json()
    assert result["analyses"]["lead_time"]["insight"] == {
        "status": "unavailable",
        "reason": "AI_NOT_CONFIGURED",
    }


def test_an_unknown_run_is_404_run_not_found(service: Service) -> None:
    for path in (f"{RUNS}/{UNKNOWN_ID}", f"{RUNS}/{UNKNOWN_ID}/result", f"{RUNS}/not-an-id"):
        response = service.get(path)
        assert (response.status_code, response.json()["code"]) == (404, "run_not_found")


def test_the_result_is_409_result_not_ready_while_the_run_is_queued(service: Service) -> None:
    run_id = service.post(request_body()).json()["run_id"]
    response = service.get(f"{RUNS}/{run_id}/result")
    assert (response.status_code, response.json()["code"]) == (409, "result_not_ready")


def test_a_crashed_run_is_failed_and_its_result_is_409_run_failed(service: Service) -> None:
    body = request_body(bookings=[booking_body(arrival_date="9999-12-31")])
    run_id = service.post(body).json()["run_id"]
    service.runner.run_all()
    state = service.get(f"{RUNS}/{run_id}").json()
    assert (state["state"], state["error_code"]) == ("failed", "analysis_failed")
    response = service.get(f"{RUNS}/{run_id}/result")
    assert (response.status_code, response.json()["code"]) == (409, "run_failed")
    assert service.post(request_body()).status_code == 202


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
def test_every_run_path_needs_the_key(service: Service, headers: dict[str, str]) -> None:
    calls: list[Callable[[], Any]] = [
        lambda: service.client.post(RUNS, content=json.dumps(request_body()), headers=headers),
        lambda: service.client.get(f"{RUNS}/{UNKNOWN_ID}", headers=headers),
        lambda: service.client.get(f"{RUNS}/{UNKNOWN_ID}/result", headers=headers),
    ]
    for call in calls:
        response = call()
        assert (response.status_code, response.json()["code"]) == (401, "unauthorized")
    assert _stored_runs(service) == []


def test_a_missing_key_wins_over_an_invalid_body(service: Service) -> None:
    response = service.client.post(RUNS, content=b"{nope")
    assert response.status_code == 401


def test_health_needs_no_key(service: Service) -> None:
    assert service.client.get("/health").json() == {"status": "ok"}


def test_holiday_validation_errors_stay_422(service: Service) -> None:
    response = service.get("/api/v1/holidays?year=abc")
    assert response.status_code == 422


def test_restart_marks_runs_left_active_as_failed_interrupted(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path / "runs")
    queued = "00000000-0000-4000-8000-0000000000a1"
    running = "00000000-0000-4000-8000-0000000000a2"
    store.save(Run.queued(queued, T0, True))
    store.save(Run.queued(running, T0, True).start(T0))
    settings = Settings(
        _env_file=None, data_source="csv", api_token="secret", output_directory=tmp_path
    )
    client = TestClient(build_app(settings))
    for run_id in (queued, running):
        state = client.get(f"{RUNS}/{run_id}", headers=KEY).json()
        assert (state["state"], state["error_code"]) == ("failed", "interrupted")
    result = client.get(f"{RUNS}/{running}/result", headers=KEY)
    assert result.json()["code"] == "run_failed"


def _generated(count: int) -> list[dict[str, Any]]:
    rng = random.Random(11)  # noqa: S311 - seeded test data
    first = date(2022, 1, 1)
    bookings = []
    for number in range(count):
        arrival = first + timedelta(days=rng.randrange(900))
        lead = rng.randrange(400)
        bookings.append(
            booking_body(
                number,
                is_canceled=rng.random() < 0.3,
                arrival_date=arrival.isoformat(),
                booking_date=(arrival - timedelta(days=lead)).isoformat(),
                lead_time=lead,
                stays_in_weekend_nights=rng.randrange(4),
                stays_in_week_nights=rng.randrange(8),
                adults=rng.randrange(1, 4),
                children=rng.randrange(3),
                country=rng.choice(["PRT", "GBR", "FRA", "DEU", "ESP"]),
                market_segment=rng.choice(["Online", "Direct", "Groups", "Corporate"]),
                customer_type=rng.choice(["Transient", "Contract", "Group"]),
                deposit_type=rng.choice(["No Deposit", "Non Refund"]),
                total_of_special_requests=rng.randrange(5),
                price_per_night=round(rng.uniform(30, 300), 2),
            )
        )
    return bookings


def test_a_run_of_55484_bookings_completes_in_under_60_seconds(service: Service) -> None:
    body = request_body(room_count=300, bookings=_generated(BOOKING_COUNT))
    started = time.perf_counter()
    response = service.post(body, insights="false")
    assert response.status_code == 202
    service.runner.run_all()
    elapsed = time.perf_counter() - started
    run_id = response.json()["run_id"]
    assert service.get(f"{RUNS}/{run_id}").json()["state"] == "completed"
    assert service.get(f"{RUNS}/{run_id}/result").json()["input"]["record_count"] == BOOKING_COUNT
    assert elapsed < TIME_LIMIT_SECONDS
