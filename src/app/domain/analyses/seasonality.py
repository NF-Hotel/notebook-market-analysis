"""Seasonality: counts by month and ISO week, by booking date and by arrival date."""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.booking import Booking
from app.domain.figures import Figure, MeanValue, make_figure, mean_of
from app.domain.period import Period, month_key

MONTHS_IN_YEAR = 12

FORMULA = (
    "Bookings are counted by booking date and arrivals by arrival date, per calendar month and "
    "per ISO week. A period figure is the records in the period over all records with the date. "
    "cancellation is the cancelled records of the period over its records. mean_price_per_night "
    "is the mean of price_per_night over the records of the period that have a price."
)
LIMITATIONS: tuple[str, ...] = (
    "A period is partial when the data starts after its first day or ends before its last day; "
    "compare partial periods with care.",
    "Only periods with at least one record are listed.",
    "A year with fewer than 12 months of data is listed in incomplete_years; a seasonal pattern "
    "needs complete years.",
    "Records without the date are left out and counted.",
    "The mean price is a mean of prices per night, not weighted by nights.",
)


@dataclass(frozen=True, slots=True)
class PeriodFigure:
    figure: Figure
    partial_period: bool
    cancellation: Figure
    mean_price_per_night: MeanValue


@dataclass(frozen=True, slots=True)
class IncompleteYear:
    year: int
    months_present: int


@dataclass(frozen=True, slots=True)
class SeasonalityMeasure:
    measure: str
    date_field: str
    span: Period | None
    records_used: int
    records_missing_date: int
    monthly: tuple[PeriodFigure, ...]
    iso_week: tuple[PeriodFigure, ...]
    incomplete_years: tuple[IncompleteYear, ...]


@dataclass(frozen=True, slots=True)
class SeasonalityAnalysis:
    bookings: SeasonalityMeasure
    arrivals: SeasonalityMeasure
    formula: str
    limitations: tuple[str, ...]


def _month_bounds(key: str) -> tuple[date, date]:
    year, month = int(key[:4]), int(key[5:])
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _week_bounds(key: str) -> tuple[date, date]:
    year, week = int(key[:4]), int(key[6:])
    monday = date.fromisocalendar(year, week, 1)
    return monday, monday + timedelta(days=6)


def _week_key(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year:04d}-W{iso.week:02d}"


def _period_figures(
    members: dict[str, list[Booking]],
    total: int,
    span: Period,
    bounds: Callable[[str], tuple[date, date]],
) -> tuple[PeriodFigure, ...]:
    figures = []
    for key in sorted(members):
        group = members[key]
        first, last = bounds(key)
        cancelled = sum(1 for b in group if b.is_canceled)
        prices = [b.price_per_night for b in group if b.price_per_night is not None]
        figures.append(
            PeriodFigure(
                make_figure(key, len(group), total),
                first < span.first_date or last > span.last_date,
                make_figure("cancellation_share", cancelled, len(group)),
                mean_of(prices),
            )
        )
    return tuple(figures)


def _incomplete_years(months: list[str]) -> tuple[IncompleteYear, ...]:
    per_year: defaultdict[int, set[str]] = defaultdict(set)
    for key in months:
        per_year[int(key[:4])].add(key)
    return tuple(
        IncompleteYear(year, len(keys))
        for year, keys in sorted(per_year.items())
        if len(keys) < MONTHS_IN_YEAR
    )


def _measure(
    bookings: list[Booking],
    measure: str,
    date_field: str,
    date_of: Callable[[Booking], date | None],
) -> SeasonalityMeasure:
    dated = [(d, b) for b in bookings if (d := date_of(b)) is not None]
    missing = len(bookings) - len(dated)
    if not dated:
        return SeasonalityMeasure(measure, date_field, None, 0, missing, (), (), ())
    span = Period(min(d for d, _ in dated), max(d for d, _ in dated))
    by_month: dict[str, list[Booking]] = defaultdict(list)
    by_week: dict[str, list[Booking]] = defaultdict(list)
    for day, booking in dated:
        by_month[month_key(day)].append(booking)
        by_week[_week_key(day)].append(booking)
    return SeasonalityMeasure(
        measure,
        date_field,
        span,
        len(dated),
        missing,
        _period_figures(by_month, len(dated), span, _month_bounds),
        _period_figures(by_week, len(dated), span, _week_bounds),
        _incomplete_years(list(by_month)),
    )


def analyse_seasonality(bookings: list[Booking]) -> SeasonalityAnalysis:
    return SeasonalityAnalysis(
        bookings=_measure(bookings, "bookings", "booking_date", lambda b: b.booking_date),
        arrivals=_measure(bookings, "arrivals", "arrival_date", lambda b: b.arrival_date),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
