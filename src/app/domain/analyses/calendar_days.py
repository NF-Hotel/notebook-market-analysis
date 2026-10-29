"""The days of a holiday calendar, as a set, and the years the calendar covers."""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.holidays import HolidayCalendar


def holiday_dates(calendar: HolidayCalendar) -> frozenset[date]:
    days: set[date] = set()
    for holiday in calendar.holidays:
        day = holiday.start_date
        while day <= holiday.end_date:
            days.add(day)
            day += timedelta(days=1)
    return frozenset(days)


def is_covered(calendar: HolidayCalendar, day: date) -> bool:
    """Whether the calendar covers the year of ``day``; outside it no day can be called holiday."""
    return calendar.first_year <= day.year <= calendar.last_year
