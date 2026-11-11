"""The holidays of the coming weeks and the bookings of the same days in earlier years."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.analyses.occupancy import nightly_counts
from app.domain.booking import Booking
from app.domain.holidays import HolidayCalendar, HolidayPeriod
from app.domain.period import Period


@dataclass(frozen=True, slots=True)
class YearHistory:
    """Room nights taken in one earlier year on the days that match the coming period."""

    year: int
    taken: int
    capacity: int

    @property
    def occupancy(self) -> float:
        return self.taken / self.capacity


class OccupancyHistory:
    """The room nights taken on every day of the bookings, for look-ups over groups of days."""

    def __init__(self, bookings: list[Booking], room_count: int, data_period: Period) -> None:
        self._room_count = room_count
        self._data_period = data_period
        counts = nightly_counts(bookings, data_period)
        self._taken = dict(zip(data_period.dates(), counts, strict=True))

    @property
    def data_period(self) -> Period:
        return self._data_period

    def year_of(self, year: int, days: Iterable[date]) -> YearHistory | None:
        """The room nights on ``days`` of ``year``; ``None`` when a day is outside the bookings."""
        found = list(days)
        if not found or any(day not in self._taken for day in found):
            return None
        return YearHistory(
            year, sum(self._taken[day] for day in found), self._room_count * len(found)
        )


def days_of(first_date: date, last_date: date) -> list[date]:
    return Period(first_date, last_date).dates()


def holidays_in_horizon(
    calendar: HolidayCalendar, first_date: date, last_date: date
) -> list[HolidayPeriod]:
    """The holidays that start inside the horizon, in date order."""
    return sorted(
        (h for h in calendar.holidays if first_date <= h.start_date <= last_date),
        key=lambda h: h.start_date,
    )


def same_holiday_in(
    calendar: HolidayCalendar, holiday: HolidayPeriod, year: int
) -> HolidayPeriod | None:
    """The holiday of the same name that starts in ``year`` (a moving holiday has another date)."""
    for other in calendar.holidays:
        if other.name == holiday.name and other.start_date.year == year:
            return other
    return None


def iso_week_days(year: int, week: int) -> list[date] | None:
    """The seven days of an ISO week; ``None`` for a week that the year does not have (week 53)."""
    monday = date.fromisocalendar(year, 1, 1) + timedelta(weeks=week - 1)
    if monday.isocalendar().week != week:
        return None
    return [monday + timedelta(days=i) for i in range(7)]


def week_blocks(first_date: date, last_date: date) -> list[Period]:
    """The horizon cut at the ISO weeks: the first and the last block may be shorter than a week."""
    blocks = []
    start = first_date
    while start <= last_date:
        end = min(start + timedelta(days=6 - start.weekday()), last_date)
        blocks.append(Period(start, end))
        start = end + timedelta(days=1)
    return blocks
