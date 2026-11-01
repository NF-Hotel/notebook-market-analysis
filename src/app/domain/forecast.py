"""Forecast: the next months of arrivals, occupancy and room revenue from the seasonal pattern.

The forecast of a calendar month is the mean of the same calendar month in the history (the
complete months of the period of the occupancy analysis). The band is one sample standard
deviation around it. It is the service's own calculation; no model takes part.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.domain.analyses.occupancy import OccupancyAnalysis
from app.domain.analyses.room_value import RoomValueAnalysis
from app.domain.booking import Booking
from app.domain.period import month_key

MEASURE_ARRIVALS = "arrivals"
MEASURE_OCCUPANCY = "occupancy"
MEASURE_ROOM_REVENUE = "room_revenue"
MINIMUM_HISTORY_MONTHS = 24  # two full years: each calendar month is seen twice
LONG_HORIZON_MONTHS = 6
SHORT_HORIZON_MONTHS = 3
LONG_HORIZON_MIN_HISTORY = 12  # one full year: each calendar month is seen once
_PLACES = Decimal("0.01")
_PERCENT = Decimal(100)

FORMULA = (
    "The history is the complete calendar months of the period of the occupancy analysis. The "
    "forecast of a month is the mean of the same calendar month in the history; when the "
    "history does not hold that calendar month it is the mean of all months of the history. "
    "The band is the forecast minus and plus one sample standard deviation of the same "
    "calendar month (of all months when the month was seen once), not below zero. Arrivals are "
    "the bookings that are not cancelled, by month of arrival; occupancy is the share of room "
    "nights taken, in percent; room revenue is as in the room value analysis, by month of "
    "arrival, and a month without a priced booking counts as zero. The forecast covers 6 "
    "months from a history of 12 months or more, else 3 months, starting the month after the "
    "last complete month."
)
LIMITATIONS: tuple[str, ...] = (
    "The forecast repeats the seasonal pattern of the history; a trend, a price change, a new "
    "event or a change of room_count is not in it.",
    "The band is the spread of the history, not a probability; the real value can lie outside it.",
    "A history shorter than 24 months is flagged as too short: with one year or less a month "
    "is seen once, and the band then rests on the spread of all months.",
    "Revenue is before taxes, fees, discounts and extras, in the price units of the input.",
)


@dataclass(frozen=True, slots=True)
class ForecastMonth:
    """The expected value of a month with its band; ``None`` when the band cannot be known."""

    month: str
    expected: Decimal
    low: Decimal | None
    high: Decimal | None


@dataclass(frozen=True, slots=True)
class MeasureForecast:
    measure: str
    unit: str
    points: tuple[ForecastMonth, ...]


@dataclass(frozen=True, slots=True)
class Forecast:
    history_months: int
    minimum_history_months: int
    history_too_short: bool
    horizon_months: int
    measures: tuple[MeasureForecast, ...]
    formula: str
    limitations: tuple[str, ...]


def _next_month(first_of_month: date) -> date:
    return (first_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)


def complete_months(occupancy: OccupancyAnalysis) -> list[date]:
    """First days of the calendar months that lie wholly inside the period, in order."""
    period = occupancy.period
    month = period.first_date.replace(day=1)
    if month < period.first_date:
        month = _next_month(month)
    months: list[date] = []
    while _next_month(month) - timedelta(days=1) <= period.last_date:
        months.append(month)
        month = _next_month(month)
    return months


def _horizon(history_months: int) -> int:
    if history_months == 0:
        return 0
    return (
        LONG_HORIZON_MONTHS if history_months >= LONG_HORIZON_MIN_HISTORY else SHORT_HORIZON_MONTHS
    )


def _rounded(value: Decimal) -> Decimal:
    return value.quantize(_PLACES, ROUND_HALF_UP)


def _forecast_month(target: date, history: Mapping[date, Decimal]) -> ForecastMonth:
    same = [v for month, v in history.items() if month.month == target.month]
    basis = same or list(history.values())
    expected = statistics.mean(basis)
    spread_basis = same if len(same) >= 2 else list(history.values())
    if len(spread_basis) < 2:
        return ForecastMonth(month_key(target), _rounded(expected), None, None)
    spread = statistics.stdev(spread_basis)
    return ForecastMonth(
        month_key(target),
        _rounded(expected),
        _rounded(max(Decimal(0), expected - spread)),
        _rounded(expected + spread),
    )


def _forecast_measure(
    measure: str,
    unit: str,
    history: Mapping[date, Decimal],
    targets: list[date],
) -> MeasureForecast:
    points = tuple(_forecast_month(t, history) for t in targets) if history else ()
    return MeasureForecast(measure, unit, points)


def _arrivals(bookings: list[Booking], months: list[date]) -> dict[date, Decimal]:
    counts = Counter(month_key(b.arrival_date) for b in bookings if not b.is_canceled)
    return {m: Decimal(counts[month_key(m)]) for m in months}


def _occupancy(occupancy: OccupancyAnalysis, months: list[date]) -> dict[date, Decimal]:
    shares = {
        f.group: Decimal(f.numerator) / Decimal(f.denominator) * _PERCENT for f in occupancy.monthly
    }
    return {m: shares[month_key(m)] for m in months}


def _revenue(room_value: RoomValueAnalysis, months: list[date]) -> dict[date, Decimal]:
    totals = {m.month: m.total for m in room_value.room_revenue.monthly}
    return {m: totals.get(month_key(m), Decimal(0)) for m in months}


def _targets(months: list[date], horizon: int) -> list[date]:
    """The months to forecast: ``horizon`` months from the one after the last complete month."""
    targets: list[date] = []
    month = _next_month(months[-1]) if months else None
    while month is not None and len(targets) < horizon:
        targets.append(month)
        month = _next_month(month)
    return targets


def forecast_market(
    bookings: list[Booking], occupancy: OccupancyAnalysis, room_value: RoomValueAnalysis
) -> Forecast:
    """The forecast of the next months from the complete months of the history."""
    months = complete_months(occupancy)
    horizon = _horizon(len(months))
    targets = _targets(months, horizon)
    return Forecast(
        history_months=len(months),
        minimum_history_months=MINIMUM_HISTORY_MONTHS,
        history_too_short=len(months) < MINIMUM_HISTORY_MONTHS,
        horizon_months=horizon,
        measures=(
            _forecast_measure(MEASURE_ARRIVALS, "bookings", _arrivals(bookings, months), targets),
            _forecast_measure(MEASURE_OCCUPANCY, "%", _occupancy(occupancy, months), targets),
            _forecast_measure(
                MEASURE_ROOM_REVENUE, "price units", _revenue(room_value, months), targets
            ),
        ),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
