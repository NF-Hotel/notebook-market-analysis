"""Port: where the state and the result of the runs are kept."""

from __future__ import annotations

from typing import Protocol

from app.application.documents import JsonObject
from app.domain.run import Run


class RunStore(Protocol):
    def save(self, run: Run) -> None:
        """Keep the state of ``run``; replaces an earlier state of the same run."""
        ...

    def load(self, run_id: str) -> Run | None:
        """The run, or None when the id is not known."""
        ...

    def active_runs(self) -> list[Run]:
        """The runs that are queued or running."""
        ...

    def save_result(self, run_id: str, result: JsonObject) -> None: ...

    def load_result(self, run_id: str) -> JsonObject | None: ...
