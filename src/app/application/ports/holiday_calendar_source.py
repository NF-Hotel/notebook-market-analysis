"""Port: the holiday calendar a run reads."""

from __future__ import annotations

from typing import Protocol

from app.domain.holidays import HolidayCalendar


class HolidayCalendarSource(Protocol):
    def covering(self, first_year: int, last_year: int) -> HolidayCalendar:
        """A calendar that covers the years given."""
        ...
