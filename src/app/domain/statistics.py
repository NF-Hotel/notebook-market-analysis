"""Median, ranks and the Spearman correlation, in pure Python."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt
from operator import mul

_PRECISION = 10


def median(values: Sequence[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle, odd = divmod(len(ordered), 2)
    if odd:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def average_ranks(values: Sequence[float]) -> list[float]:
    """Ranks from 1; values that tie share the mean of the ranks they span."""
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        shared = (start + end) / 2 + 1
        for position in range(start, end + 1):
            ranks[order[position]] = shared
        start = end + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Spearman rank correlation; ``None`` for fewer than 2 pairs or a constant series."""
    if len(xs) != len(ys):
        raise ValueError("the series must have the same length")
    if len(xs) < 2 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return pearson(average_ranks(xs), average_ranks(ys))


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    spread = sqrt(sum(map(mul, dx, dx)) * sum(map(mul, dy, dy)))
    if spread == 0:
        return None
    value = float(sum(map(mul, dx, dy))) / spread
    return round(max(-1.0, min(1.0, value)), _PRECISION)
