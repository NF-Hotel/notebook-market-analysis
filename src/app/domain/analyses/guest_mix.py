"""Guest mix: how the bookings are spread over guest and stay traits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.domain.booking import Booking
from app.domain.figures import Figure, MeanValue, make_figure, mean_of

FORMULA = (
    "A distribution figure is the bookings with the trait value over all bookings that have the "
    "trait. For each value: mean_length_of_stay is the mean nights, cancellation_share the "
    "cancelled bookings over the bookings of the value, mean_price_per_night the mean price "
    "per night of the bookings that have a price. Total guests is adults plus children plus "
    "babies."
)
LIMITATIONS: tuple[str, ...] = (
    "Bookings that lack a trait are left out of its distribution and counted in records_left_out.",
    "A difference between values is an association; the values differ in other traits too.",
    "A value with fewer than 30 bookings is flagged small_sample and its means are unreliable.",
    "Total guests counts a missing adults, children or babies value as zero when another of the "
    "three is known.",
)


@dataclass(frozen=True, slots=True)
class GuestGroup:
    figure: Figure
    mean_length_of_stay: MeanValue
    cancellation_share: Figure
    mean_price_per_night: MeanValue


@dataclass(frozen=True, slots=True)
class Distribution:
    field: str
    records_used: int
    records_left_out: int
    groups: tuple[GuestGroup, ...]


@dataclass(frozen=True, slots=True)
class GuestMixAnalysis:
    total_guests: Distribution
    country: Distribution
    meal: Distribution
    assigned_room_type: Distribution
    is_repeated_guest: Distribution
    required_car_parking_spaces: Distribution
    total_of_special_requests: Distribution
    formula: str
    limitations: tuple[str, ...]


def _text(value: int | None) -> str | None:
    return None if value is None else str(value)


def _repeated(booking: Booking) -> str | None:
    if booking.is_repeated_guest is None:
        return None
    return "repeated" if booking.is_repeated_guest else "not_repeated"


def _distribution(
    field: str,
    bookings: list[Booking],
    key: Callable[[Booking], str | None],
    numeric: bool = False,
) -> Distribution:
    members: dict[str, list[Booking]] = {}
    for booking in bookings:
        label = key(booking)
        if label is not None:
            members.setdefault(label, []).append(booking)
    used = sum(len(group) for group in members.values())
    if numeric:
        labels = sorted(members, key=int)
    else:
        labels = sorted(members, key=lambda g: (-len(members[g]), g))
    groups = tuple(
        GuestGroup(
            figure=make_figure(label, len(members[label]), used),
            mean_length_of_stay=mean_of(b.nights for b in members[label]),
            cancellation_share=make_figure(
                "cancellation_share",
                sum(1 for b in members[label] if b.is_canceled),
                len(members[label]),
            ),
            mean_price_per_night=mean_of(
                p for b in members[label] if (p := b.price_per_night) is not None
            ),
        )
        for label in labels
    )
    return Distribution(field, used, len(bookings) - used, groups)


def analyse_guest_mix(bookings: list[Booking]) -> GuestMixAnalysis:
    return GuestMixAnalysis(
        total_guests=_distribution(
            "total_guests", bookings, lambda b: _text(b.total_guests), numeric=True
        ),
        country=_distribution("country", bookings, lambda b: b.country or None),
        meal=_distribution("meal", bookings, lambda b: b.meal),
        assigned_room_type=_distribution(
            "assigned_room_type", bookings, lambda b: b.assigned_room_type
        ),
        is_repeated_guest=_distribution("is_repeated_guest", bookings, _repeated),
        required_car_parking_spaces=_distribution(
            "required_car_parking_spaces",
            bookings,
            lambda b: _text(b.required_car_parking_spaces),
            numeric=True,
        ),
        total_of_special_requests=_distribution(
            "total_of_special_requests",
            bookings,
            lambda b: _text(b.total_of_special_requests),
            numeric=True,
        ),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
