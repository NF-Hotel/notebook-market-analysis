"""Fakes of the run ports and the body of a run request, for the tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.application.documents import JsonObject
from app.domain.run import Run

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class FakeRunStore:
    def __init__(self) -> None:
        self.runs: dict[str, Run] = {}
        self.results: dict[str, JsonObject] = {}

    def save(self, run: Run) -> None:
        self.runs[run.run_id] = run

    def load(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    def active_runs(self) -> list[Run]:
        return [r for r in self.runs.values() if r.is_active]

    def save_result(self, run_id: str, result: JsonObject) -> None:
        self.results[run_id] = result

    def load_result(self, run_id: str) -> JsonObject | None:
        return self.results.get(run_id)


class ManualTaskRunner:
    """Keeps the tasks until the test runs them, so a test sees each state in between."""

    def __init__(self) -> None:
        self.tasks: list[Callable[[], None]] = []

    def submit(self, task: Callable[[], None]) -> None:
        self.tasks.append(task)

    def run_all(self) -> None:
        while self.tasks:
            self.tasks.pop(0)()


class SteppingClock:
    """A clock that moves one second at each reading."""

    def __init__(self) -> None:
        self._now = T0

    def __call__(self) -> datetime:
        self._now += timedelta(seconds=1)
        return self._now


class SequentialIds:
    """Valid, distinct run and result ids."""

    def __init__(self) -> None:
        self._count = 0

    def __call__(self) -> str:
        self._count += 1
        return f"00000000-0000-4000-8000-{self._count:012d}"


class RecordingInsightProvider:
    """A fake AI provider; ``on_call`` lets a test look at the service while a run is running."""

    def __init__(self, on_call: Callable[[], None] | None = None) -> None:
        self.names: list[str] = []
        self.on_call = on_call

    def info(self) -> dict[str, str]:
        return {"provider": "fake", "model": "fake-1", "prompt_version": "1"}

    def insight_for(self, name: str, analysis: JsonObject) -> JsonObject:
        self.names.append(name)
        if self.on_call is not None:
            self.on_call()
        return {"status": "available", "executive_summary": f"About {name}."}


def booking_body(number: int = 1, **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    body: dict[str, Any] = {
        "booking_id": number,
        "hotel": "City Hotel",
        "is_canceled": False,
        "arrival_date": "2024-01-01",
        "stays_in_weekend_nights": 0,
        "stays_in_week_nights": 2,
        "country": "PRT",
    }
    body.update(changes)
    return body


def request_body(**changes: Any) -> dict[str, Any]:  # noqa: ANN401
    body: dict[str, Any] = {"room_count": 2, "bookings": [booking_body()]}
    body.update(changes)
    return body
