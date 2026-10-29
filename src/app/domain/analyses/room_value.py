"""Room value: length of stay and an ESTIMATE of the value of the rooms booked."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from app.domain.booking import Booking
from app.domain.figures import Figure, MeanValue, make_figure, mean_of

ESTIMATE_NOTICE_CODE = "ESTIMATE_NOT_REVENUE"
ESTIMATE_LABEL = (
    "Estimate in the price units of the input: price per night times nights. It is not revenue."
)
STAY_BUCKETS: tuple[str, ...] = ("1", "2", "3", "4", "5-7", "8+")
# The highest number of nights of each bucket but the last, in order.
_BUCKET_LIMITS = tuple(zip((1, 2, 3, 4, 7), STAY_BUCKETS[:-1], strict=True))

FORMULA = (
    "Length of stay is the weekend nights plus the week nights. The buckets are 1, 2, 3, 4, 5-7 "
    "and 8+ nights; a bucket figure is the records in it over the records with at least one "
    "night. The estimated value of a booking is price_per_night times nights, in the price units "
    "of the input; total is the sum and mean the mean over the bookings that have a price."
)
LIMITATIONS: tuple[str, ...] = (
    "The estimated value is an ESTIMATE, not revenue: taxes, fees, discounts, extras, the "
    "currency and what a cancelled guest paid are not known.",
    "Bookings of no nights are left out and counted in zero_night_records.",
    "Bookings without a price are left out of the value and counted; a price of zero is "
    "included and counted in zero_price_records.",
    "Cancelled bookings are valued like the others, so the value of cancelled bookings is not "
    "money lost.",
)


@dataclass(frozen=True, slots=True)
class EstimatedValueGroup:
    figure: Figure
    value_per_booking: MeanValue
    total: Decimal
    records_without_price: int
    zero_price_records: int


@dataclass(frozen=True, slots=True)
class RoomValueAnalysis:
    estimate_notice_code: str
    estimate_label: str
    records_used: int
    zero_night_records: int
    total_nights: int
    length_of_stay: tuple[Figure, ...]
    records_without_price: int
    zero_price_records: int
    overall: EstimatedValueGroup
    by_cancellation_status: tuple[EstimatedValueGroup, ...]
    formula: str
    limitations: tuple[str, ...]


def stay_bucket(nights: int) -> str:
    for limit, label in _BUCKET_LIMITS:
        if nights <= limit:
            return label
    return STAY_BUCKETS[-1]


def _value_group(label: str, group: list[Booking], total: int) -> EstimatedValueGroup:
    values = [v for b in group if (v := b.estimated_value) is not None]
    return EstimatedValueGroup(
        figure=make_figure(label, len(group), total),
        value_per_booking=mean_of(values),
        total=sum(values, Decimal(0)),
        records_without_price=len(group) - len(values),
        zero_price_records=sum(1 for b in group if b.price_per_night == 0),
    )


def analyse_room_value(bookings: list[Booking]) -> RoomValueAnalysis:
    stays = [b for b in bookings if b.nights > 0]
    in_bucket = Counter(stay_bucket(b.nights) for b in stays)
    cancelled = [b for b in stays if b.is_canceled]
    kept = [b for b in stays if not b.is_canceled]
    overall = _value_group("all", stays, len(stays))
    return RoomValueAnalysis(
        estimate_notice_code=ESTIMATE_NOTICE_CODE,
        estimate_label=ESTIMATE_LABEL,
        records_used=len(stays),
        zero_night_records=len(bookings) - len(stays),
        total_nights=sum(b.nights for b in stays),
        length_of_stay=tuple(make_figure(g, in_bucket[g], len(stays)) for g in STAY_BUCKETS),
        records_without_price=overall.records_without_price,
        zero_price_records=overall.zero_price_records,
        overall=overall,
        by_cancellation_status=(
            _value_group("canceled", cancelled, len(stays)),
            _value_group("not_canceled", kept, len(stays)),
        ),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
