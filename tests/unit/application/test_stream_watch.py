import pytest

from app.application.ports.model_client import ModelTimeoutError, TimeLimits
from app.application.stream_watch import StreamWatch
from tests.unit.ai_fakes import FakeMonotonicClock


def test_tokens_inside_both_limits_are_accepted() -> None:
    clock = FakeMonotonicClock()
    watch = StreamWatch(TimeLimits(stall_seconds=10, total_seconds=100), clock)
    for _ in range(5):
        clock.advance(9.9)
        watch.token()


def test_a_gap_of_the_stall_timeout_between_tokens_is_given_up() -> None:
    clock = FakeMonotonicClock()
    watch = StreamWatch(TimeLimits(stall_seconds=10, total_seconds=100), clock)
    clock.advance(10)
    with pytest.raises(ModelTimeoutError):
        watch.token()


def test_the_first_token_counts_from_the_start_of_the_request() -> None:
    clock = FakeMonotonicClock()
    watch = StreamWatch(TimeLimits(stall_seconds=10, total_seconds=100), clock)
    clock.advance(9.9)
    watch.token()


def test_tokens_that_keep_coming_are_stopped_at_the_total_limit() -> None:
    clock = FakeMonotonicClock()
    watch = StreamWatch(TimeLimits(stall_seconds=10, total_seconds=100), clock)
    for _ in range(10):
        clock.advance(10 - 0.1)
        watch.token()
    clock.advance(10 - 0.1)
    with pytest.raises(ModelTimeoutError):
        watch.token()
