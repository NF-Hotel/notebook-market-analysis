"""Price suggestions for the coming weeks from the bookings: a fixed rule, no AI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction
from typing import Literal

from app.domain.analyses.occupancy import resolve_period
from app.domain.analyses.price_history import (
    OccupancyHistory,
    YearHistory,
    days_of,
    holidays_in_horizon,
    iso_week_days,
    same_holiday_in,
    week_blocks,
)
from app.domain.booking import Booking
from app.domain.errors import InvalidRequest
from app.domain.holidays import HolidayCalendar, HolidayPeriod
from app.domain.period import Period

Change = Literal["surcharge", "discount"]
Reason = Literal["holiday", "high_history", "low_history"]

FORMULA = (
    "For each holiday and each week of the horizon the occupancy of the same holiday, or of the "
    "same ISO week, is added up over the earlier years of the bookings: room nights taken over "
    "room_count times the days. At or above the high threshold a surcharge is suggested for every "
    "room size; at or below the low threshold a discount is suggested for the sizes that qualify. "
    "A period with fewer earlier years than the minimum gets no suggestion."
)
LIMITATIONS: tuple[str, ...] = (
    "The occupancy is that of the whole hotel; it is not known by room size, so a discount for a "
    "size rests on the occupancy of all rooms.",
    "A year counts only when all its days of the period lie inside the bookings.",
    "Cancelled bookings take no room night; the history shows what was taken, not what was asked.",
    "The suggestion is a percentage of the base rate; the service does not know a room rate.",
)


@dataclass(frozen=True, slots=True)
class PricingSettings:
    as_of: date
    horizon_days: int = 61
    high_occupancy_threshold: str = "0.80"
    low_occupancy_threshold: str = "0.40"
    surcharge_percent: str = "20"
    discount_percent: str = "15"
    discount_room_sizes: tuple[str, ...] = ("single",)
    min_history_years: int = 2

    def __post_init__(self) -> None:
        high, low = self.high, self.low
        if not 7 <= self.horizon_days <= 120:
            raise InvalidRequest("horizon_days must be between 7 and 120")
        if not (0 <= low < high <= 1):
            raise InvalidRequest(
                "the low threshold must be below the high threshold, within 0 to 1"
            )
        if not 0 < Fraction(self.surcharge_percent) <= 100:
            raise InvalidRequest("surcharge_percent must be above 0 and at most 100")
        if not 0 < Fraction(self.discount_percent) < 100:
            raise InvalidRequest("discount_percent must be above 0 and below 100")
        if not 1 <= self.min_history_years <= 10:
            raise InvalidRequest("min_history_years must be between 1 and 10")

    @property
    def high(self) -> Fraction:
        return Fraction(self.high_occupancy_threshold)

    @property
    def low(self) -> Fraction:
        return Fraction(self.low_occupancy_threshold)

    @property
    def horizon_end(self) -> date:
        return self.as_of + timedelta(days=self.horizon_days - 1)


@dataclass(frozen=True, slots=True)
class PriceSuggestion:
    room_size: str
    first_date: date
    last_date: date
    change: Change
    percent: str
    reason: Reason
    holiday: str | None
    threshold: str
    history: tuple[YearHistory, ...]


@dataclass(frozen=True, slots=True)
class NotEnoughHistory:
    first_date: date
    last_date: date
    holiday: str | None
    years_found: int


@dataclass(frozen=True, slots=True)
class PriceSuggestionSet:
    as_of: date
    horizon_end: date
    suggestions: tuple[PriceSuggestion, ...]
    not_enough_history: tuple[NotEnoughHistory, ...]
    formula: str
    limitations: tuple[str, ...]


def suggest_prices(
    bookings: list[Booking],
    room_count: int,
    calendar: HolidayCalendar,
    settings: PricingSettings,
    period: Period | None = None,
) -> PriceSuggestionSet:
    history = OccupancyHistory(bookings, room_count, resolve_period(bookings, period))
    suggestions: list[PriceSuggestion] = []
    missing: list[NotEnoughHistory] = []
    holiday_days: set[date] = set()
    for holiday in holidays_in_horizon(calendar, settings.as_of, settings.horizon_end):
        days = days_of(holiday.start_date, holiday.end_date)
        holiday_days.update(days)
        years = _holiday_years(history, calendar, holiday)
        _judge(
            suggestions,
            missing,
            settings,
            years,
            holiday.start_date,
            holiday.end_date,
            holiday.name,
            "holiday",
        )
    for block in week_blocks(settings.as_of, settings.horizon_end):
        years = _week_years(history, block.first_date)
        for first, last in _runs(block, holiday_days):
            _judge(suggestions, missing, settings, years, first, last, None, "high_history")
    return PriceSuggestionSet(
        as_of=settings.as_of,
        horizon_end=settings.horizon_end,
        suggestions=tuple(suggestions),
        not_enough_history=tuple(missing),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )


def _holiday_years(
    history: OccupancyHistory, calendar: HolidayCalendar, holiday: HolidayPeriod
) -> list[YearHistory]:
    found = []
    for year in range(history.data_period.first_date.year, holiday.start_date.year):
        earlier = same_holiday_in(calendar, holiday, year)
        if earlier is None:
            continue
        year_history = history.year_of(year, days_of(earlier.start_date, earlier.end_date))
        if year_history is not None:
            found.append(year_history)
    return found


def _week_years(history: OccupancyHistory, day: date) -> list[YearHistory]:
    iso_year, week, _ = day.isocalendar()
    found = []
    for year in range(history.data_period.first_date.year, iso_year):
        days = iso_week_days(year, week)
        year_history = history.year_of(year, days) if days is not None else None
        if year_history is not None:
            found.append(year_history)
    return found


def _runs(block: Period, holiday_days: set[date]) -> list[tuple[date, date]]:
    """The stretches of the block that are not holidays (a holiday has its own suggestion)."""
    runs: list[tuple[date, date]] = []
    start: date | None = None
    for day in block.dates():
        if day in holiday_days:
            if start is not None:
                runs.append((start, day - timedelta(days=1)))
                start = None
        elif start is None:
            start = day
    if start is not None:
        runs.append((start, block.last_date))
    return runs


def _judge(
    suggestions: list[PriceSuggestion],
    missing: list[NotEnoughHistory],
    settings: PricingSettings,
    years: list[YearHistory],
    first: date,
    last: date,
    holiday: str | None,
    kind: Reason,
) -> None:
    if len(years) < settings.min_history_years:
        missing.append(NotEnoughHistory(first, last, holiday, len(years)))
        return
    share = Fraction(sum(y.taken for y in years), sum(y.capacity for y in years))
    if share >= settings.high:
        suggestions.append(
            PriceSuggestion(
                "all",
                first,
                last,
                "surcharge",
                settings.surcharge_percent,
                "holiday" if kind == "holiday" else "high_history",
                holiday,
                settings.high_occupancy_threshold,
                tuple(years),
            )
        )
    elif share <= settings.low:
        suggestions.extend(
            PriceSuggestion(
                size,
                first,
                last,
                "discount",
                settings.discount_percent,
                "low_history",
                holiday,
                settings.low_occupancy_threshold,
                tuple(years),
            )
            for size in settings.discount_room_sizes
        )
