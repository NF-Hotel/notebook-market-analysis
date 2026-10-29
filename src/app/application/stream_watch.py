"""Enforces the two time limits of a streamed model request."""

from __future__ import annotations

from collections.abc import Callable

from app.application.ports.model_client import ModelTimeoutError, TimeLimits

# Seconds from a monotonic clock; a test passes a fake one so that nothing sleeps.
MonotonicClock = Callable[[], float]


class StreamWatch:
    """Call ``token()`` for every token that arrives; it raises when a limit is reached.

    The adapter also gives its HTTP client the stall timeout as read timeout, so a stream that
    goes silent is given up even though no token arrives to call ``token()``.
    """

    def __init__(self, limits: TimeLimits, clock: MonotonicClock) -> None:
        self._limits = limits
        self._clock = clock
        self._started = clock()
        self._last_token = self._started

    def token(self) -> None:
        now = self._clock()
        if now - self._started >= self._limits.total_seconds:
            raise ModelTimeoutError(
                f"the request ran for the total limit of {self._limits.total_seconds}s"
            )
        if now - self._last_token >= self._limits.stall_seconds:
            raise ModelTimeoutError(
                f"no token for the stall timeout of {self._limits.stall_seconds}s"
            )
        self._last_token = now
