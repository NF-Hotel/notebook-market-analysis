"""Use cases of the market analysis run: start, execute in the background, state and result."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial

from app.application.analyse_market import analyse_market
from app.application.documents import JsonObject
from app.application.market_result import build_market_result
from app.application.ports.holiday_calendar_source import HolidayCalendarSource
from app.application.ports.insight_provider import InsightProvider
from app.application.ports.run_store import RunStore
from app.application.ports.task_runner import TaskRunner
from app.domain.booking import Booking
from app.domain.errors import (
    InvalidRequest,
    ResultNotReady,
    RunAlreadyActive,
    RunFailed,
    RunNotFound,
)
from app.domain.period import Period
from app.domain.run import (
    ERROR_ANALYSIS_FAILED,
    ERROR_INTERRUPTED,
    ERROR_START_FAILED,
    Run,
    RunState,
)

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


@dataclass(frozen=True, slots=True)
class StartRunCommand:
    bookings: list[Booking]
    room_count: int
    period: Period | None
    insights: bool


def _validate(command: StartRunCommand) -> None:
    if not command.bookings:
        raise InvalidRequest("at least one booking is needed")
    if command.room_count < 1:
        raise InvalidRequest("room_count must be at least 1")


class ExecuteRun:
    """Runs the analyses of one queued run and keeps its state and result."""

    def __init__(
        self,
        store: RunStore,
        calendars: HolidayCalendarSource,
        insights: InsightProvider,
        clock: Clock,
        new_id: IdFactory,
    ) -> None:
        self._store = store
        self._calendars = calendars
        self._insights = insights
        self._clock = clock
        self._new_id = new_id

    def execute(self, run_id: str, command: StartRunCommand) -> None:
        """Never raises: a failure is kept as the state ``failed`` with an error code."""
        try:
            run = self._require(run_id).start(self._clock())
            self._store.save(run)
            self._store.save_result(run_id, self._analyse(command))
            self._store.save(run.complete(self._clock()))
        except Exception:
            # A run must end as completed or failed, never stay running, whatever went wrong.
            logger.exception("market analysis run %s failed", run_id)
            self._fail(run_id, ERROR_ANALYSIS_FAILED)

    def _require(self, run_id: str) -> Run:
        run = self._store.load(run_id)
        if run is None:
            raise RunNotFound(run_id)
        return run

    def _analyse(self, command: StartRunCommand) -> JsonObject:
        bookings = command.bookings
        first_year, last_year = _years_of(bookings, command.period)
        calendar = self._calendars.covering(first_year, last_year)
        analysis = analyse_market(bookings, command.room_count, calendar, command.period)
        return build_market_result(
            analysis,
            bookings,
            calendar,
            self._new_id(),
            self._clock(),
            self._insights if command.insights else None,
        )

    def _fail(self, run_id: str, error_code: str) -> None:
        try:
            self._store.save(self._require(run_id).fail(self._clock(), error_code))
        except Exception:
            logger.exception("market analysis run %s could not be marked failed", run_id)


def _years_of(bookings: list[Booking], period: Period | None) -> tuple[int, int]:
    """The years the analyses can touch: bookings, stays and the period."""
    days = [b.arrival_date for b in bookings] + [b.departure_date for b in bookings]
    days += [b.booking_date for b in bookings if b.booking_date is not None]
    if period is not None:
        days += [period.first_date, period.last_date]
    return min(days).year, max(days).year


class StartRun:
    """Queues a run when no other run is active and hands it to the background runner."""

    def __init__(
        self,
        store: RunStore,
        runner: TaskRunner,
        execute: ExecuteRun,
        clock: Clock,
        new_id: IdFactory,
    ) -> None:
        self._store = store
        self._runner = runner
        self._execute = execute
        self._clock = clock
        self._new_id = new_id
        self._lock = threading.Lock()

    def start(self, command: StartRunCommand) -> Run:
        """Return the queued run at once. Nothing is stored when the request is refused."""
        _validate(command)
        with self._lock:
            if self._store.active_runs():
                raise RunAlreadyActive("another run is queued or running")
            run = Run.queued(self._new_id(), self._clock(), command.insights)
            self._store.save(run)
            self._submit(run, command)
        return run

    def _submit(self, run: Run, command: StartRunCommand) -> None:
        try:
            self._runner.submit(partial(self._execute.execute, run.run_id, command))
        except Exception:
            self._store.save(run.fail(self._clock(), ERROR_START_FAILED))
            raise


class GetRun:
    def __init__(self, store: RunStore) -> None:
        self._store = store

    def get(self, run_id: str) -> Run:
        run = self._store.load(run_id)
        if run is None:
            raise RunNotFound(f"run {run_id} is not known")
        return run


class GetRunResult:
    def __init__(self, store: RunStore) -> None:
        self._store = store
        self._runs = GetRun(store)

    def get(self, run_id: str) -> JsonObject:
        run = self._runs.get(run_id)
        if run.state is RunState.FAILED:
            raise RunFailed(f"run {run_id} failed: {run.error_code}")
        if run.state is not RunState.COMPLETED:
            raise ResultNotReady(f"run {run_id} is {run.state}")
        result = self._store.load_result(run_id)
        if result is None:
            raise ResultNotReady(f"the result of run {run_id} is missing")
        return result


class RecoverInterruptedRuns:
    """At start-up: a run left queued or running by a restart will never finish."""

    def __init__(self, store: RunStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def recover(self) -> int:
        """Mark each such run failed (``interrupted``); returns how many."""
        active = self._store.active_runs()
        for run in active:
            self._store.save(run.fail(self._clock(), ERROR_INTERRUPTED))
        return len(active)
