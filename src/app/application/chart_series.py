"""The charts of an analysis: the series that can be read out of its ``findings``.

This is the same rule the web application uses to draw its charts
(``FindingsSeries.cs``), because an observation of the AI is matched to a chart by the
``id`` of its series. Change the two together.

A group figure is an object with ``group`` and ``numerator`` and ``denominator`` (a share, in
percent), or ``value``, or ``count``; it sits directly in a list or wrapped as
``{"figure": {...}}``. A list of such items is one series whose id is the dotted path of the
list inside the findings (``splits.by_deposit_type.groups``). Two or more group figures that
sit directly in the findings are one series with the property names joined by ``+``
(``holiday_days+other_days``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.application.documents import JsonObject

MAX_POINTS = 30
MAX_CHART_POINTS = 60
MAX_SERIES = 8

_GROUP = "group"
_FIGURE = "figure"
_GENERIC_NAMES = frozenset({"groups", "splits", "periods", "distributions", "buckets"})
_MONTH_LABEL = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_PERCENT = 100


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    label: str
    value: float
    numerator: float | None = None
    denominator: float | None = None


@dataclass(frozen=True, slots=True)
class ChartSeries:
    id: str
    title: str
    unit: str
    points: tuple[SeriesPoint, ...]


@dataclass(frozen=True, slots=True)
class _Figure:
    value: float
    unit: str
    numerator: float | None = None
    denominator: float | None = None


def chart_series(findings: JsonObject) -> list[ChartSeries]:
    """The series of the findings, overview first, at most ``MAX_SERIES``."""
    found: list[tuple[int, ChartSeries]] = []
    _walk(findings, [], found)
    compared = _root_figures(findings)
    if compared is not None:
        found.append((0, compared))
    kept = [
        entry
        for entry in found
        if _is_monthly(entry[1]) or len(entry[1].points) <= MAX_CHART_POINTS
    ]
    kept.sort(key=lambda entry: (entry[0], len(entry[1].points)))  # stable
    return [_shorten(series) for _, series in kept][:MAX_SERIES]


def _is_monthly(series: ChartSeries) -> bool:
    return bool(series.points) and all(_MONTH_LABEL.match(p.label) for p in series.points)


def _shorten(series: ChartSeries) -> ChartSeries:
    count = len(series.points)
    if count <= MAX_POINTS:
        return series
    if _is_monthly(series):
        title = f"{series.title} (latest {MAX_POINTS} of {count} months)"
        return ChartSeries(series.id, title, series.unit, series.points[-MAX_POINTS:])
    return ChartSeries(series.id, series.title, series.unit, series.points[:MAX_POINTS])


def _walk(node: Any, path: list[str], found: list[tuple[int, ChartSeries]]) -> None:  # noqa: ANN401 - JSON
    if isinstance(node, dict):
        # A part the service marks unavailable holds placeholders, not figures.
        if node.get("status") == "unavailable":
            return
        for name, child in node.items():
            _walk(child, [*path, name], found)
    elif isinstance(node, list):
        series = _to_series(node, path)
        if series is not None:
            found.append((len(path), series))
            return
        for index, item in enumerate(node):
            _walk(item, [*path, str(index)], found)


def _to_series(items: list[Any], path: list[str]) -> ChartSeries | None:
    points: list[SeriesPoint] = []
    unit = ""
    for item in items:
        wrapped = item.get(_FIGURE) if isinstance(item, dict) else None
        figure_item = wrapped if isinstance(wrapped, dict) else item
        if not isinstance(figure_item, dict) or _GROUP not in figure_item:
            return None
        figure = _figure(figure_item)
        if figure is None:
            continue
        unit = unit or figure.unit
        points.append(
            SeriesPoint(
                _label(figure_item[_GROUP]), figure.value, figure.numerator, figure.denominator
            )
        )
    if not points:
        return None
    return ChartSeries(".".join(path), _title(path), unit, tuple(points))


def _root_figures(findings: JsonObject) -> ChartSeries | None:
    names: list[str] = []
    points: list[SeriesPoint] = []
    for name, child in findings.items():
        if isinstance(child, dict) and isinstance(child.get(_GROUP), str):
            figure = _figure(child)
            if figure is not None:
                names.append(name)
                points.append(
                    SeriesPoint(_humanize(name), figure.value, figure.numerator, figure.denominator)
                )
    if len(points) < 2:
        return None
    return ChartSeries("+".join(names), _comparison_title(names), "%", tuple(points))


def _figure(item: dict[str, Any]) -> _Figure | None:
    numerator = _number(item, "numerator")
    denominator = _number(item, "denominator")
    if numerator is not None and denominator is not None:
        if denominator <= 0:
            return None
        share = round(numerator / denominator * _PERCENT, 1)
        return _Figure(share, "%", numerator, denominator)
    value = _number(item, "value")
    if value is not None:
        return _Figure(value, "")
    count = _number(item, "count")
    return _Figure(count, "bookings") if count is not None else None


def _number(item: dict[str, Any], name: str) -> float | None:
    """A number, or a decimal string (money is a string in the markets API)."""
    value = item.get(name)
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _label(group: Any) -> str:  # noqa: ANN401 - any JSON value
    if isinstance(group, str):
        return group
    if group is None:
        return ""
    if isinstance(group, bool):
        return "True" if group else "False"
    return json.dumps(group, ensure_ascii=False, separators=(",", ":"))


def _humanize(name: str) -> str:
    text = name.replace("_", " ")
    return name if not text else text[0].upper() + text[1:]


def _comparison_title(names: list[str]) -> str:
    words = [name.replace("_", " ") for name in names]
    return words[0][0].upper() + " and ".join(words)[1:]


def _title(path: list[str]) -> str:
    words = [p for p in path if p not in _GENERIC_NAMES and not p.isdecimal()][-2:]
    text = " - ".join(word.replace("_", " ") for word in words)
    return "Groups" if not text else text[0].upper() + text[1:]
