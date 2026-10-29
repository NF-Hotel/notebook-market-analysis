"""Port: runs a task in the background, one at a time."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class TaskRunner(Protocol):
    def submit(self, task: Callable[[], None]) -> None:
        """Queue ``task`` and return at once; tasks run one after the other."""
        ...
