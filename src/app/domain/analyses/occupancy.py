"""Occupancy: the share of room nights that are taken."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.booking import Booking
from app.domain.errors import InvalidRequest
from app.domain.figures import Figure, make_figure
from app.domain.period import Period, month_key

FORMULA = (
    "Occupancy is the room nights taken over room_count times the nights of the period. A room "
    "night is taken from the arrival to the day before the departure (arrival plus nights, "
    "minus one day); only nights inside the period count. Cancelled bookings take no room "
    "night. The period is the given one, or from the first arrival to the last night taken."
)
LIMITATIONS: tuple[str, ...] = (
    "room_count is the number of rooms the caller gives; rooms that are closed or out of order "
    "are not known.",
    "Cancelled bookings are taken as empty rooms; a no-show or a late cancellation that was paid "
    "is not known.",
    "A booking of no nights takes no room night.",
    "Nothing is capped: a share above 100 % means the bookings hold more room nights than "
    "room_count rooms can, for example overbooking or a room_count that is too low.",
    "Bookings that start before the period or end after it count only inside it; a period "
    "shorter than the bookings' span ignores the rest of them.",
)
OVER_CAPACITY_LIMITATION = (
    "On {days} day(s) of the period the room nights taken exceeded room_count; the shares are "
    "not capped and can be above 100 %."
)


@dataclass(frozen=True, slots=True)
class OccupancyAnalysis:
    room_count: int
    period: Period
    overall: Figure
    monthly: tuple[Figure, ...]
    over_capacity_days: int
    formula: str
    limitations: tuple[str, ...]


def resolve_period(bookings: list[Booking], period: Period | None) -> Period:
    """The given period, or the span from the first arrival to the last night taken."""
    if period is not None:
        return period
    if not bookings:
        raise InvalidRequest("a period is needed when there are no bookings")
    first = min(b.arrival_date for b in bookings)
    last = max(b.last_night or b.arrival_date for b in bookings)
    return Period(first, last)


def nightly_counts(bookings: list[Booking], period: Period) -> list[int]:
    """Room nights taken on each day of the period (cancelled bookings and other days left out)."""
    change = [0] * (period.days + 1)
    for booking in bookings:
        last_night = booking.last_night
        if booking.is_canceled or last_night is None:
            continue
        start = max(booking.arrival_date, period.first_date)
        end = min(last_night, period.last_date)
        if start > end:
            continue
        change[(start - period.first_date).days] += 1
        change[(end - period.first_date).days + 1] -= 1
    counts = []
    running = 0
    for delta in change[:-1]:
        running += delta
        counts.append(running)
    return counts


def validate_room_count(room_count: int) -> None:
    if room_count < 1:
        raise InvalidRequest("room_count must be at least 1")


def analyse_occupancy(
    bookings: list[Booking], room_count: int, period: Period | None = None
) -> OccupancyAnalysis:
    validate_room_count(room_count)
    resolved = resolve_period(bookings, period)
    counts = nightly_counts(bookings, resolved)
    days = resolved.dates()
    taken: dict[str, int] = {}
    day_count: dict[str, int] = {}
    for day, count in zip(days, counts, strict=True):
        key = month_key(day)
        taken[key] = taken.get(key, 0) + count
        day_count[key] = day_count.get(key, 0) + 1
    over = sum(1 for count in counts if count > room_count)
    limitations = LIMITATIONS
    if over:
        limitations = (*LIMITATIONS, OVER_CAPACITY_LIMITATION.format(days=over))
    return OccupancyAnalysis(
        room_count=room_count,
        period=resolved,
        overall=make_figure("overall", sum(counts), room_count * len(days)),
        monthly=tuple(make_figure(k, taken[k], room_count * day_count[k]) for k in sorted(taken)),
        over_capacity_days=over,
        formula=FORMULA,
        limitations=limitations,
    )
