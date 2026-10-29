"""A market analysis run: its state and the times it changed."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from app.domain.errors import InvalidRunTransition

ERROR_INTERRUPTED = "interrupted"
ERROR_ANALYSIS_FAILED = "analysis_failed"
ERROR_START_FAILED = "start_failed"


class RunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Run:
    """One run. Each change returns a new run; a finished run cannot change again."""

    run_id: str
    state: RunState
    created_at: datetime
    insights_requested: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None

    @classmethod
    def queued(cls, run_id: str, now: datetime, insights_requested: bool) -> Run:
        return cls(run_id, RunState.QUEUED, now, insights_requested)

    @property
    def is_active(self) -> bool:
        return self.state in (RunState.QUEUED, RunState.RUNNING)

    def start(self, now: datetime) -> Run:
        self._require(RunState.QUEUED, RunState.RUNNING)
        return replace(self, state=RunState.RUNNING, started_at=now)

    def complete(self, now: datetime) -> Run:
        self._require(RunState.RUNNING, RunState.COMPLETED)
        return replace(self, state=RunState.COMPLETED, finished_at=now)

    def fail(self, now: datetime, error_code: str) -> Run:
        """Fail a queued or running run; ``error_code`` says why."""
        self._require_active(RunState.FAILED)
        return replace(self, state=RunState.FAILED, finished_at=now, error_code=error_code)

    def _require(self, expected: RunState, target: RunState) -> None:
        if self.state is not expected:
            raise InvalidRunTransition(f"a {self.state} run cannot become {target}")

    def _require_active(self, target: RunState) -> None:
        if not self.is_active:
            raise InvalidRunTransition(f"a {self.state} run cannot become {target}")
