"""Correlations: Spearman rank correlation between the numeric booking fields and cancelled."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.domain.booking import Booking
from app.domain.statistics import average_ranks, pearson

METHOD = "spearman"
_MIN_PAIRS = 2

FORMULA = (
    "Spearman rank correlation: the Pearson correlation of the ranks of two fields, with tied "
    "values given the mean of their ranks. A pair uses the bookings that have both values. "
    "is_canceled is 1 for a cancelled booking and 0 otherwise. The value is between -1 and 1, "
    "or null when a field is constant in the pair or fewer than 2 bookings have both values."
)
LIMITATIONS: tuple[str, ...] = (
    "A correlation shows that two fields move together; it does not show that one causes the "
    "other.",
    "Spearman finds a steady rise or fall, not other shapes of relation.",
    "A value is null when it cannot be calculated; bookings with a missing value are left out of "
    "each pair, so pairs rest on different bookings (see records_used).",
    "Fields that are text or flags other than is_canceled are not in the matrix.",
)

_FIELD_GETTERS: dict[str, Callable[[Booking], float | None]] = {
    "lead_time": lambda b: b.lead_time,
    "stays_in_weekend_nights": lambda b: b.stays_in_weekend_nights,
    "stays_in_week_nights": lambda b: b.stays_in_week_nights,
    "adults": lambda b: b.adults,
    "children": lambda b: b.children,
    "babies": lambda b: b.babies,
    "previous_cancellations": lambda b: b.previous_cancellations,
    "booking_changes": lambda b: b.booking_changes,
    "required_car_parking_spaces": lambda b: b.required_car_parking_spaces,
    "total_of_special_requests": lambda b: b.total_of_special_requests,
    # Only the order of the prices matters for a rank, so a float is exact enough here.
    "price_per_night": lambda b: None if b.price_per_night is None else float(b.price_per_night),
    "is_canceled": lambda b: 1.0 if b.is_canceled else 0.0,
}
FIELDS: tuple[str, ...] = tuple(_FIELD_GETTERS)


@dataclass(frozen=True, slots=True)
class CorrelationsAnalysis:
    method: str
    fields: tuple[str, ...]
    matrix: tuple[tuple[float | None, ...], ...]
    records_used: tuple[int, ...]
    formula: str
    limitations: tuple[str, ...]


class _RankCache:
    """Ranks of a field over the bookings of a mask, kept so equal masks rank once."""

    def __init__(self, columns: list[list[float | None]]) -> None:
        self._columns = columns
        self._mask_ids: dict[bytes, int] = {}
        self._indices: dict[int, list[int]] = {}
        self._ranks: dict[tuple[int, int], list[float]] = {}

    def mask_id(self, mask: bytes) -> int:
        known = self._mask_ids.get(mask)
        if known is not None:
            return known
        mask_id = len(self._mask_ids)
        self._mask_ids[mask] = mask_id
        self._indices[mask_id] = [i for i, flag in enumerate(mask) if flag]
        return mask_id

    def count(self, mask_id: int) -> int:
        return len(self._indices[mask_id])

    def ranks(self, field: int, mask_id: int) -> list[float]:
        key = (field, mask_id)
        if key not in self._ranks:
            column = self._columns[field]
            values = [column[i] for i in self._indices[mask_id]]
            self._ranks[key] = average_ranks([v for v in values if v is not None])
        return self._ranks[key]


def _pair(cache: _RankCache, a: int, b: int, mask: bytes) -> float | None:
    mask_id = cache.mask_id(mask)
    if cache.count(mask_id) < _MIN_PAIRS:
        return None
    return pearson(cache.ranks(a, mask_id), cache.ranks(b, mask_id))


def analyse_correlations(bookings: list[Booking]) -> CorrelationsAnalysis:
    columns = [[getter(b) for b in bookings] for getter in _FIELD_GETTERS.values()]
    present = [bytes(0 if v is None else 1 for v in column) for column in columns]
    cache = _RankCache(columns)
    size = len(FIELDS)
    matrix: list[list[float | None]] = [[None] * size for _ in range(size)]
    for a in range(size):
        for b in range(a, size):
            mask = bytes(x & y for x, y in zip(present[a], present[b], strict=True))
            matrix[a][b] = matrix[b][a] = _pair(cache, a, b, mask)
    return CorrelationsAnalysis(
        method=METHOD,
        fields=FIELDS,
        matrix=tuple(tuple(row) for row in matrix),
        records_used=tuple(sum(mask) for mask in present),
        formula=FORMULA,
        limitations=LIMITATIONS,
    )
