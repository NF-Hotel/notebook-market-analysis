"""Cancellations: the share of bookings that were cancelled, overall and by group."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.domain.analyses.lead_time import BAND_LABELS, lead_time_band
from app.domain.booking import Booking
from app.domain.figures import Figure, count_figures, make_figure
from app.domain.period import month_key

FORMULA = (
    "The cancellation share of a group is the cancelled bookings of the group over all its "
    "bookings. Lead time bands are 0-7, 8-30, 31-90 and 91+ days."
)
LIMITATIONS: tuple[str, ...] = (
    "A share is an observed association between a booking trait and cancellation, not a cause.",
    "Bookings that lack the trait of a split are left out of that split and counted in "
    "records_left_out.",
    "The groups of a split are not independent of each other (a long lead time is more common "
    "in some market segments).",
    "Whether a booking was cancelled is as the data says; no cancellation date is known.",
)


@dataclass(frozen=True, slots=True)
class CancellationSplit:
    records_used: int
    records_left_out: int
    groups: tuple[Figure, ...]


@dataclass(frozen=True, slots=True)
class CancellationAnalysis:
    records_used: int
    overall: Figure
    by_lead_time_band: CancellationSplit
    by_deposit_type: CancellationSplit
    by_market_segment: CancellationSplit
    by_customer_type: CancellationSplit
    by_arrival_month: CancellationSplit
    by_special_requests: CancellationSplit
    by_booking_changes: CancellationSplit
    formula: str
    limitations: tuple[str, ...]


def _split(
    bookings: list[Booking],
    key: Callable[[Booking], str | None],
    order: Callable[[str], int | str] | None = None,
) -> CancellationSplit:
    groups = count_figures(bookings, key, lambda b: b.is_canceled, order)
    used = sum(g.denominator for g in groups)
    return CancellationSplit(used, len(bookings) - used, groups)


def _text(value: int | None) -> str | None:
    return None if value is None else str(value)


def analyse_cancellations(bookings: list[Booking]) -> CancellationAnalysis:
    cancelled = sum(1 for b in bookings if b.is_canceled)
    return CancellationAnalysis(
        records_used=len(bookings),
        overall=make_figure("all", cancelled, len(bookings)),
        by_lead_time_band=_split(
            bookings,
            lambda b: None if b.lead_time is None else lead_time_band(b.lead_time),
            BAND_LABELS.index,
        ),
        by_deposit_type=_split(bookings, lambda b: b.deposit_type),
        by_market_segment=_split(bookings, lambda b: b.market_segment),
        by_customer_type=_split(bookings, lambda b: b.customer_type),
        by_arrival_month=_split(bookings, lambda b: month_key(b.arrival_date), str),
        by_special_requests=_split(bookings, lambda b: _text(b.total_of_special_requests), int),
        by_booking_changes=_split(bookings, lambda b: _text(b.booking_changes), int),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
