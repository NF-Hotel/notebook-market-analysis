"""Runs the background tasks of the service on one worker thread, one after the other."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor


class ThreadTaskRunner:
    def __init__(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="market-analysis-run")

    def submit(self, task: Callable[[], None]) -> None:
        self._pool.submit(task)

    def close(self) -> None:
        """Wait for the running task and stop the worker."""
        self._pool.shutdown(wait=True)
