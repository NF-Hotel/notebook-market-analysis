"""Keeps each run in the output volume: ``<root>/<run_id>/state.json`` and ``result.json``."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.adapters.storage.atomic_json import write_json_atomically
from app.application.documents import JsonObject
from app.domain.run import Run, RunState

logger = logging.getLogger(__name__)

STATE_FILE = "state.json"
RESULT_FILE = "result.json"


def _is_run_id(value: str) -> bool:
    """Only a canonical UUID names a run, so an id can never leave the root folder."""
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _optional_time(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _state_data(run: Run) -> JsonObject:
    return {
        "run_id": run.run_id,
        "state": run.state.value,
        "created_at": run.created_at.isoformat(),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error_code": run.error_code,
        "insights_requested": run.insights_requested,
    }


def _run_of(data: JsonObject) -> Run:
    return Run(
        run_id=data["run_id"],
        state=RunState(data["state"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        insights_requested=bool(data["insights_requested"]),
        started_at=_optional_time(data["started_at"]),
        finished_at=_optional_time(data["finished_at"]),
        error_code=data["error_code"],
    )


class FileRunStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, run: Run) -> None:
        write_json_atomically(self._root / run.run_id / STATE_FILE, _state_data(run))

    def load(self, run_id: str) -> Run | None:
        if not _is_run_id(run_id):
            return None
        return self._read_state(self._root / run_id / STATE_FILE)

    def active_runs(self) -> list[Run]:
        if not self._root.is_dir():
            return []
        runs = (self.load(folder.name) for folder in self._root.iterdir() if folder.is_dir())
        return [run for run in runs if run is not None and run.is_active]

    def save_result(self, run_id: str, result: JsonObject) -> None:
        write_json_atomically(self._root / run_id / RESULT_FILE, result)

    def load_result(self, run_id: str) -> JsonObject | None:
        if not _is_run_id(run_id):
            return None
        try:
            data: JsonObject = json.loads(
                (self._root / run_id / RESULT_FILE).read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None
        return data

    @staticmethod
    def _read_state(path: Path) -> Run | None:
        try:
            return _run_of(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError):
            # A damaged state file is a run that cannot be read; it is not a run that is active.
            logger.warning("the state file %s cannot be read", path)
            return None
