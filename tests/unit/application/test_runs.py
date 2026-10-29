from datetime import date
from decimal import Decimal

import pytest

from app.application.holidays import HolidayService
from app.application.insights import UnconfiguredInsightProvider
from app.application.ports.insight_provider import InsightProvider
from app.application.runs import (
    ExecuteRun,
    GetRun,
    GetRunResult,
    RecoverInterruptedRuns,
    StartRun,
    StartRunCommand,
)
from app.domain.booking import Booking
from app.domain.errors import (
    InvalidRequest,
    ResultNotReady,
    RunAlreadyActive,
    RunFailed,
    RunNotFound,
)
from app.domain.holidays import HolidayCalendar
from app.domain.period import Period
from app.domain.run import Run, RunState
from tests.unit.booking_factory import make_booking
from tests.unit.run_fakes import (
    T0,
    FakeRunStore,
    ManualTaskRunner,
    RecordingInsightProvider,
    SequentialIds,
    SteppingClock,
)


class EmptyHolidayStore:
    def load(self) -> HolidayCalendar | None:
        return None

    def save(self, calendar: HolidayCalendar) -> None:
        raise AssertionError("a run must not store a calendar")


class Setup:
    def __init__(self, insights: InsightProvider | None = None) -> None:
        self.store = FakeRunStore()
        self.runner = ManualTaskRunner()
        clock, ids = SteppingClock(), SequentialIds()
        self.execute = ExecuteRun(
            self.store,
            HolidayService(EmptyHolidayStore()),
            insights or UnconfiguredInsightProvider(),
            clock,
            ids,
        )
        self.start = StartRun(self.store, self.runner, self.execute, clock, ids)
        self.get = GetRun(self.store)
        self.result = GetRunResult(self.store)


def _command(
    bookings: list[Booking] | None = None,
    room_count: int = 2,
    period: Period | None = None,
    insights: bool = True,
) -> StartRunCommand:
    complete = [make_booking(lead_time=10, price_per_night=Decimal(100))]
    return StartRunCommand(bookings or complete, room_count, period, insights)


def _crashing() -> StartRunCommand:
    # a stay that starts on the last day of the calendar overflows the date arithmetic
    return _command([make_booking(arrival_date=date(9999, 12, 31))])


def test_start_returns_a_queued_run_and_runs_nothing_yet() -> None:
    setup = Setup()
    run = setup.start.start(_command())
    assert run.state is RunState.QUEUED
    assert setup.get.get(run.run_id).state is RunState.QUEUED
    assert len(setup.runner.tasks) == 1


def test_the_run_completes_when_the_runner_runs_it() -> None:
    setup = Setup()
    run = setup.start.start(_command())
    setup.runner.run_all()
    done = setup.get.get(run.run_id)
    assert done.state is RunState.COMPLETED
    assert done.started_at is not None
    assert done.finished_at is not None
    assert setup.result.get(run.run_id)["schema_version"] == "1.1"


def test_a_second_start_while_one_is_queued_is_refused() -> None:
    setup = Setup()
    setup.start.start(_command())
    with pytest.raises(RunAlreadyActive) as refused:
        setup.start.start(_command())
    assert refused.value.code == "run_active"
    assert len(setup.store.runs) == 1


def test_a_new_run_can_start_after_the_last_one_finished() -> None:
    setup = Setup()
    setup.start.start(_command())
    setup.runner.run_all()
    assert setup.start.start(_command()).state is RunState.QUEUED


@pytest.mark.parametrize(
    "command",
    [
        StartRunCommand([], 2, None, True),
        StartRunCommand([make_booking()], 0, None, True),
        StartRunCommand([make_booking()], -3, None, True),
    ],
    ids=["empty-list", "no-rooms", "negative-rooms"],
)
def test_an_invalid_request_is_refused_and_nothing_is_stored(command: StartRunCommand) -> None:
    setup = Setup()
    with pytest.raises(InvalidRequest):
        setup.start.start(command)
    assert setup.store.runs == {}
    assert setup.runner.tasks == []


def test_a_crash_in_a_run_gives_failed_with_a_code() -> None:
    setup = Setup()
    run = setup.start.start(_crashing())
    setup.runner.run_all()
    failed = setup.get.get(run.run_id)
    assert (failed.state, failed.error_code) == (RunState.FAILED, "analysis_failed")
    assert setup.store.active_runs() == []


def test_a_failed_run_frees_the_slot() -> None:
    setup = Setup()
    setup.start.start(_crashing())
    setup.runner.run_all()
    assert setup.start.start(_command()).state is RunState.QUEUED


def test_a_runner_that_refuses_the_task_fails_the_run() -> None:
    setup = Setup()

    class RefusingRunner:
        def submit(self, task: object) -> None:
            raise RuntimeError("shut down")

    start = StartRun(setup.store, RefusingRunner(), setup.execute, SteppingClock(), SequentialIds())
    with pytest.raises(RuntimeError):
        start.start(_command())
    (run,) = setup.store.runs.values()
    assert (run.state, run.error_code) == (RunState.FAILED, "start_failed")


def test_unknown_run_is_not_found() -> None:
    setup = Setup()
    with pytest.raises(RunNotFound):
        setup.get.get("nope")
    with pytest.raises(RunNotFound):
        setup.result.get("nope")


def test_result_is_not_ready_while_queued_and_running() -> None:
    setup = Setup()
    run = setup.start.start(_command())
    with pytest.raises(ResultNotReady):
        setup.result.get(run.run_id)
    setup.store.save(run.start(T0))
    with pytest.raises(ResultNotReady):
        setup.result.get(run.run_id)


def test_result_of_a_failed_run_is_refused_with_run_failed() -> None:
    setup = Setup()
    setup.store.save(Run.queued("r", T0, True).fail(T0, "analysis_failed"))
    with pytest.raises(RunFailed):
        setup.result.get("r")


def test_the_state_is_running_while_the_run_works() -> None:
    provider = RecordingInsightProvider()
    setup = Setup(provider)
    seen: list[RunState] = []
    run = setup.start.start(_command())
    provider.on_call = lambda: seen.append(setup.get.get(run.run_id).state)
    setup.runner.run_all()
    assert seen
    assert set(seen) == {RunState.RUNNING}


def test_without_insights_the_provider_is_not_called_and_no_insight_key() -> None:
    provider = RecordingInsightProvider()
    setup = Setup(provider)
    run = setup.start.start(_command(insights=False))
    setup.runner.run_all()
    result = setup.result.get(run.run_id)
    assert provider.names == []
    assert all("insight" not in a for a in result["analyses"].values())
    assert result["insights"] == {"requested": False}
    assert result["status"] == "completed"


def test_with_insights_and_no_provider_every_analysis_is_unavailable() -> None:
    setup = Setup()
    run = setup.start.start(_command())
    setup.runner.run_all()
    result = setup.result.get(run.run_id)
    insights = [a["insight"] for a in result["analyses"].values()]
    assert len(insights) == 9
    assert all(i == {"status": "unavailable", "reason": "AI_NOT_CONFIGURED"} for i in insights)
    assert result["status"] == "completed_with_warnings"
    assert [n["code"] for n in result["notices"]] == ["INSIGHTS_UNAVAILABLE"]


def test_with_a_provider_the_insights_and_their_source_are_in_the_result() -> None:
    provider = RecordingInsightProvider()
    setup = Setup(provider)
    run = setup.start.start(_command())
    setup.runner.run_all()
    result = setup.result.get(run.run_id)
    assert len(provider.names) == 9
    assert result["insights"]["provider"] == "fake"
    assert result["analyses"]["occupancy"]["insight"]["status"] == "available"


def test_the_period_of_the_request_is_used() -> None:
    setup = Setup()
    period = Period(date(2024, 1, 1), date(2024, 1, 10))
    run = setup.start.start(_command(period=period, insights=False))
    setup.runner.run_all()
    result = setup.result.get(run.run_id)
    assert result["input"]["period"] == {"first_date": "2024-01-01", "last_date": "2024-01-10"}


def test_interrupted_runs_are_marked_failed_at_start_up() -> None:
    store = FakeRunStore()
    store.save(Run.queued("a", T0, True))
    store.save(Run.queued("b", T0, True).start(T0))
    store.save(Run.queued("c", T0, True).start(T0).complete(T0))
    assert RecoverInterruptedRuns(store, SteppingClock()).recover() == 2
    assert store.runs["a"].error_code == "interrupted"
    assert store.runs["b"].state is RunState.FAILED
    assert store.runs["c"].state is RunState.COMPLETED
    assert store.active_runs() == []
