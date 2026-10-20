"""Keeps the holiday calendar as one JSON file."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

from app.domain.holidays import HolidayCalendar, HolidayPeriod


class FileHolidayStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> HolidayCalendar | None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return HolidayCalendar(
                data["country"],
                data["source"],
                int(data["first_year"]),
                int(data["last_year"]),
                tuple(
                    HolidayPeriod(
                        h["name"],
                        date.fromisoformat(h["start_date"]),
                        date.fromisoformat(h["end_date"]),
                    )
                    for h in data["holidays"]
                ),
            )
        except (OSError, ValueError, KeyError, TypeError):
            # Missing or damaged: the caller generates a new calendar.
            return None

    def save(self, calendar: HolidayCalendar) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "country": calendar.country,
            "source": calendar.source,
            "first_year": calendar.first_year,
            "last_year": calendar.last_year,
            "holidays": [
                {
                    "name": h.name,
                    "start_date": h.start_date.isoformat(),
                    "end_date": h.end_date.isoformat(),
                }
                for h in calendar.holidays
            ],
        }
        # Write beside the target and replace, so a reader never sees half a file.
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.replace(tmp, self._path)
