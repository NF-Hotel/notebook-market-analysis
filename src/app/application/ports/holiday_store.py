"""Port: where the generated holiday calendar is kept between requests."""

from __future__ import annotations

from typing import Protocol

from app.domain.holidays import HolidayCalendar


class HolidayStore(Protocol):
    def load(self) -> HolidayCalendar | None:
        """The stored calendar, or None if none has been generated yet."""
        ...

    def save(self, calendar: HolidayCalendar) -> None: ...
