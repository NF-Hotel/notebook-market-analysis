"""Lead time: the days between the booking and the arrival."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from app.domain.booking import Booking
from app.domain.figures import Figure, make_figure
from app.domain.period import month_key
from app.domain.statistics import median

BAND_LABELS: tuple[str, ...] = ("0-7", "8-30", "31-90", "91+")
_BAND_LIMITS = (7, 30, 90)

FORMULA = (
    "Lead time is the supplied lead_time in days. Bands: 0-7, 8-30, 31-90 and 91+ days. "
    "A band figure is the records in the band over the records of its group. The median is the "
    "middle value of the lead times of the group (the mean of the two middle values when the "
    "count is even). A group figure is the records of the group over all records with a lead time."
)
LIMITATIONS: tuple[str, ...] = (
    "Records without a lead time are left out and counted in records_without_lead_time.",
    "The supplied lead time is used as it is; it is not checked against the booking date.",
    "The analysis describes how far ahead guests book; it does not say why.",
)


def lead_time_band(days: int) -> str:
    for label, limit in zip(BAND_LABELS, _BAND_LIMITS, strict=False):
        if days <= limit:
            return label
    return BAND_LABELS[-1]


@dataclass(frozen=True, slots=True)
class LeadTimeGroup:
    """The lead times of one group: its share of the records, its median and its bands."""

    figure: Figure
    median_days: float | None
    bands: tuple[Figure, ...]


@dataclass(frozen=True, slots=True)
class LeadTimeAnalysis:
    unit: str
    records_used: int
    records_without_lead_time: int
    overall: LeadTimeGroup
    by_cancellation_status: tuple[LeadTimeGroup, ...]
    by_arrival_month: tuple[LeadTimeGroup, ...]
    by_market_segment: tuple[LeadTimeGroup, ...]
    by_customer_type: tuple[LeadTimeGroup, ...]
    formula: str
    limitations: tuple[str, ...]


def _group(label: str, days: list[int], total: int) -> LeadTimeGroup:
    in_band = Counter(lead_time_band(d) for d in days)
    bands = tuple(make_figure(band, in_band[band], len(days)) for band in BAND_LABELS)
    return LeadTimeGroup(make_figure(label, len(days), total), median(days), bands)


def _split(
    used: list[Booking],
    key: Callable[[Booking], str | None],
    chronological: bool = False,
) -> tuple[LeadTimeGroup, ...]:
    members: dict[str, list[int]] = {}
    for booking in used:
        label = key(booking)
        if label is not None and booking.lead_time is not None:
            members.setdefault(label, []).append(booking.lead_time)
    if chronological:
        labels = sorted(members)
    else:
        labels = sorted(members, key=lambda g: (-len(members[g]), g))
    return tuple(_group(label, members[label], len(used)) for label in labels)


def analyse_lead_time(bookings: list[Booking]) -> LeadTimeAnalysis:
    used = [b for b in bookings if b.lead_time is not None]
    days = [b.lead_time for b in used if b.lead_time is not None]
    return LeadTimeAnalysis(
        unit="days",
        records_used=len(used),
        records_without_lead_time=len(bookings) - len(used),
        overall=_group("all", days, len(used)),
        by_cancellation_status=_split(
            used, lambda b: "canceled" if b.is_canceled else "not_canceled"
        ),
        by_arrival_month=_split(used, lambda b: month_key(b.arrival_date), chronological=True),
        by_market_segment=_split(used, lambda b: b.market_segment),
        by_customer_type=_split(used, lambda b: b.customer_type),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
