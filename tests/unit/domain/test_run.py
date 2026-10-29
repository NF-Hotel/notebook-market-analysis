import pytest

from app.domain.errors import InvalidRunTransition
from app.domain.run import Run, RunState
from tests.unit.run_fakes import T0


def _queued() -> Run:
    return Run.queued("r", T0, True)


def test_a_new_run_is_queued_and_active() -> None:
    run = _queued()
    assert run.state is RunState.QUEUED
    assert run.is_active


def test_run_goes_from_queued_to_running_to_completed() -> None:
    running = _queued().start(T0)
    assert (running.state, running.started_at) == (RunState.RUNNING, T0)
    done = running.complete(T0)
    assert (done.state, done.finished_at, done.is_active) == (RunState.COMPLETED, T0, False)


@pytest.mark.parametrize("run", [_queued(), _queued().start(T0)])
def test_an_active_run_can_fail_with_a_code(run: Run) -> None:
    failed = run.fail(T0, "boom")
    assert (failed.state, failed.error_code) == (RunState.FAILED, "boom")


def test_a_queued_run_cannot_complete() -> None:
    with pytest.raises(InvalidRunTransition):
        _queued().complete(T0)


def test_a_finished_run_cannot_change_again() -> None:
    done = _queued().start(T0).complete(T0)
    with pytest.raises(InvalidRunTransition):
        done.fail(T0, "late")
    with pytest.raises(InvalidRunTransition):
        done.start(T0)
