"""A share with the counts it rests on, and the small helpers that build it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

SMALL_SAMPLE_LIMIT = 30
_MEAN_PLACES = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class Figure:
    """``numerator`` of ``denominator``; ``small_sample`` when the denominator is below 30."""

    group: str
    numerator: int
    denominator: int
    small_sample: bool

    @property
    def share(self) -> float | None:
        if self.denominator == 0:
            return None
        return self.numerator / self.denominator


def make_figure(group: str, numerator: int, denominator: int) -> Figure:
    return Figure(group, numerator, denominator, denominator < SMALL_SAMPLE_LIMIT)


@dataclass(frozen=True, slots=True)
class MeanValue:
    """A mean of ``count`` values; ``value`` is ``None`` when there is no value."""

    value: Decimal | None
    count: int
    small_sample: bool


def mean_of(values: Iterable[Decimal | int]) -> MeanValue:
    """The mean rounded to four places (half up); missing values are not passed in."""
    items = [Decimal(v) for v in values]
    if not items:
        return MeanValue(None, 0, True)
    mean = (sum(items, Decimal(0)) / len(items)).quantize(_MEAN_PLACES, ROUND_HALF_UP)
    return MeanValue(mean, len(items), len(items) < SMALL_SAMPLE_LIMIT)


def count_figures[T](
    items: Iterable[T],
    key: Callable[[T], str | None],
    flagged: Callable[[T], bool] | None = None,
    order: Callable[[str], int | str] | None = None,
) -> tuple[Figure, ...]:
    """One figure per group key; items whose key is ``None`` are left out.

    Without ``flagged`` the numerator is the group size and the denominator the number of items
    that have a key. With ``flagged`` the numerator is the number of flagged items in the group
    and the denominator the group size. Groups are ordered by ``order`` of the key, or by size
    (largest first) and then by key.
    """
    sizes: Counter[str] = Counter()
    hits: Counter[str] = Counter()
    for item in items:
        group = key(item)
        if group is None:
            continue
        sizes[group] += 1
        if flagged is not None and flagged(item):
            hits[group] += 1
    total = sum(sizes.values())
    groups = sorted(sizes, key=order) if order else sorted(sizes, key=lambda g: (-sizes[g], g))
    if flagged is None:
        return tuple(make_figure(g, sizes[g], total) for g in groups)
    return tuple(make_figure(g, hits[g], sizes[g]) for g in groups)
