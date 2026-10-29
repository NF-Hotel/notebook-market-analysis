"""Occupancy on holidays: the share of room nights taken on holiday days and on other days."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.analyses.calendar_days import holiday_dates, is_covered
from app.domain.analyses.occupancy import nightly_counts, resolve_period, validate_room_count
from app.domain.booking import Booking
from app.domain.figures import Figure, make_figure
from app.domain.holidays import HolidayCalendar
from app.domain.period import Period

FORMULA = (
    "Occupancy is the room nights taken over room_count times the number of days. The holiday "
    "days figure uses the days of the period that are holidays in the calendar, the other days "
    "figure the remaining days of the period. A room night is taken from the arrival to the day "
    "before the departure; cancelled bookings take none."
)
LIMITATIONS: tuple[str, ...] = (
    "Days in years that the holiday calendar does not cover are left out of both figures and "
    "counted in days_left_out_unavailable_years.",
    "The difference between holiday days and other days is an association; weekends, seasons and "
    "events fall on holidays too.",
    "A holiday that falls in a short period gives a small sample.",
    "Nothing is capped: a share above 100 % means more room nights than room_count rooms.",
    "Cancelled bookings are taken as empty rooms.",
)


@dataclass(frozen=True, slots=True)
class OccupancyOnHolidaysAnalysis:
    room_count: int
    period: Period
    holiday_days: Figure
    other_days: Figure
    days_left_out_unavailable_years: int
    formula: str
    limitations: tuple[str, ...]


def analyse_occupancy_on_holidays(
    bookings: list[Booking],
    room_count: int,
    calendar: HolidayCalendar,
    period: Period | None = None,
) -> OccupancyOnHolidaysAnalysis:
    validate_room_count(room_count)
    resolved = resolve_period(bookings, period)
    counts = nightly_counts(bookings, resolved)
    holidays = holiday_dates(calendar)
    taken = {"holiday_days": 0, "other_days": 0}
    days = {"holiday_days": 0, "other_days": 0}
    left_out = 0
    for day, count in zip(resolved.dates(), counts, strict=True):
        if not is_covered(calendar, day):
            left_out += 1
            continue
        kind = "holiday_days" if day in holidays else "other_days"
        taken[kind] += count
        days[kind] += 1
    return OccupancyOnHolidaysAnalysis(
        room_count=room_count,
        period=resolved,
        holiday_days=make_figure(
            "holiday_days", taken["holiday_days"], room_count * days["holiday_days"]
        ),
        other_days=make_figure("other_days", taken["other_days"], room_count * days["other_days"]),
        days_left_out_unavailable_years=left_out,
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
