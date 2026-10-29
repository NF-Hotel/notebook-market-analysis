"""Use cases for the holiday calendar served to the NF Hotel web application."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from app.application.ports.holiday_store import HolidayStore
from app.domain.holidays import MAX_YEAR, MIN_YEAR, HolidayCalendar, build_calendar, validate_years

# A new calendar covers the previous, the current and the next two years.
_YEARS_BEFORE = 1
_YEARS_AFTER = 2


class HolidayService:
    def __init__(self, store: HolidayStore, today: Callable[[], date] = date.today) -> None:
        self._store = store
        self._today = today

    def get(self, year: int | None = None) -> HolidayCalendar:
        """The stored calendar (made first if there is none), limited to ``year`` if given."""
        calendar = self._store.load()
        if calendar is None:
            calendar = self._generate(None, None)
        if year is None:
            return calendar
        validate_years(year, year)
        return calendar.for_year(year)

    def update(self, first_year: int | None, last_year: int | None) -> HolidayCalendar:
        """Generate the calendar from scratch and store it."""
        return self._generate(first_year, last_year)

    def _generate(self, first_year: int | None, last_year: int | None) -> HolidayCalendar:
        current = self._today().year
        first = first_year if first_year is not None else current - _YEARS_BEFORE
        last = last_year if last_year is not None else max(first, current + _YEARS_AFTER)
        calendar = build_calendar(first, last)
        self._store.save(calendar)
        return calendar

    def covering(self, first_year: int, last_year: int) -> HolidayCalendar:
        """The stored calendar if it covers the years, else one built for them (not stored).

        Years outside 1900 to 2200 are left out; the analyses report them as unavailable.
        """
        first = min(max(first_year, MIN_YEAR), MAX_YEAR)
        last = min(max(last_year, MIN_YEAR), MAX_YEAR)
        stored = self._store.load()
        if stored is not None and stored.first_year <= first and last <= stored.last_year:
            return stored
        return build_calendar(first, last)
