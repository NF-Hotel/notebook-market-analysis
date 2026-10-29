"""Holidays: bookings and arrivals on holiday days against the same weekdays on other days."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.analyses.calendar_days import holiday_dates, is_covered
from app.domain.booking import Booking
from app.domain.figures import Figure, make_figure
from app.domain.holidays import HolidayCalendar
from app.domain.period import Period

WINDOWS_DAYS: tuple[int, ...] = (1, 3, 7)

FORMULA = (
    "A day group is the holiday days of the calendar, or the non-holiday days within 1, 3 or 7 "
    "days before or after a holiday. Its figure is the bookings (or arrivals) on those days over "
    "the number of those days in the span of the data, zero-booking days included; mean_per_day "
    "is that ratio. The baseline is the days of the span that are neither holiday nor in the "
    "group and fall on a weekday that the group has. cancellation_share (arrivals only) is the "
    "cancelled arrivals of the group over its arrivals."
)
LIMITATIONS: tuple[str, ...] = (
    "The span is from the first to the last date in the data; days outside the years of the "
    "holiday calendar are left out and the years are listed in years_unavailable.",
    "A difference between holiday days and the baseline is an association, not a cause.",
    "Holidays in other countries, school holidays and events are not in the calendar.",
    "Records without the date are left out and counted.",
)


@dataclass(frozen=True, slots=True)
class DayGroup:
    figure: Figure
    mean_per_day: float | None
    cancellation: Figure | None


@dataclass(frozen=True, slots=True)
class HolidayComparison:
    day_kind: str
    window_days: int | None
    group: DayGroup
    baseline: DayGroup


@dataclass(frozen=True, slots=True)
class HolidayMeasure:
    measure: str
    date_field: str
    span: Period | None
    records_used: int
    records_missing_date: int
    records_left_out_unavailable_years: int
    years_unavailable: tuple[int, ...]
    holiday: HolidayComparison | None
    windows: tuple[HolidayComparison, ...]


@dataclass(frozen=True, slots=True)
class HolidayAnalysis:
    windows_days: tuple[int, ...]
    booking_date: HolidayMeasure
    arrival_date: HolidayMeasure
    formula: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Counts:
    records: Counter[date]
    cancelled: Counter[date]
    track_cancellation: bool


def _day_group(label: str, days: list[date], counts: _Counts) -> DayGroup:
    records = sum(counts.records[d] for d in days)
    figure = make_figure(label, records, len(days))
    cancellation = None
    if counts.track_cancellation:
        cancelled = sum(counts.cancelled[d] for d in days)
        cancellation = make_figure("cancellation_share", cancelled, records)
    return DayGroup(figure, figure.share, cancellation)


def _comparison(
    kind: str,
    window: int | None,
    label: str,
    group_days: list[date],
    usable: list[date],
    holidays: frozenset[date],
    counts: _Counts,
) -> HolidayComparison:
    in_group = set(group_days)
    weekdays = {d.weekday() for d in group_days}
    baseline_days = [
        d for d in usable if d not in holidays and d not in in_group and d.weekday() in weekdays
    ]
    return HolidayComparison(
        kind,
        window,
        _day_group(label, group_days, counts),
        _day_group("baseline_same_weekdays", baseline_days, counts),
    )


def _near_holiday(day: date, window: int, direction: int, all_holidays: frozenset[date]) -> bool:
    return any(day + timedelta(days=direction * n) in all_holidays for n in range(1, window + 1))


def _measure(
    bookings: list[Booking],
    measure: str,
    date_field: str,
    date_of: Callable[[Booking], date | None],
    calendar: HolidayCalendar,
    track_cancellation: bool,
) -> HolidayMeasure:
    dated = [(d, b) for b in bookings if (d := date_of(b)) is not None]
    used = [(d, b) for d, b in dated if is_covered(calendar, d)]
    missing = len(bookings) - len(dated)
    left_out = len(dated) - len(used)
    if not dated:
        return HolidayMeasure(measure, date_field, None, 0, missing, 0, (), None, ())
    span = Period(min(d for d, _ in dated), max(d for d, _ in dated))
    all_days = span.dates()
    usable = [d for d in all_days if is_covered(calendar, d)]
    unavailable = tuple(sorted({d.year for d in all_days if not is_covered(calendar, d)}))
    counts = _Counts(
        Counter(d for d, _ in used),
        Counter(d for d, b in used if b.is_canceled),
        track_cancellation,
    )
    all_holidays = holiday_dates(calendar)
    holidays = frozenset(d for d in usable if d in all_holidays)
    holiday_days = [d for d in usable if d in holidays]
    windows = tuple(
        _comparison(
            kind,
            window,
            f"{kind}_{window}_days",
            [
                d
                for d in usable
                if d not in holidays and _near_holiday(d, window, sign, all_holidays)
            ],
            usable,
            holidays,
            counts,
        )
        for window in WINDOWS_DAYS
        for kind, sign in (("before", 1), ("after", -1))
    )
    return HolidayMeasure(
        measure,
        date_field,
        span,
        len(used),
        missing,
        left_out,
        unavailable,
        _comparison("holiday", None, "holiday", holiday_days, usable, holidays, counts),
        windows,
    )


def analyse_holidays(bookings: list[Booking], calendar: HolidayCalendar) -> HolidayAnalysis:
    return HolidayAnalysis(
        windows_days=WINDOWS_DAYS,
        booking_date=_measure(
            bookings, "bookings", "booking_date", lambda b: b.booking_date, calendar, False
        ),
        arrival_date=_measure(
            bookings, "arrivals", "arrival_date", lambda b: b.arrival_date, calendar, True
        ),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
