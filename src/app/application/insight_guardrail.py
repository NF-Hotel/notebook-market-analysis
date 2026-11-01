"""The guardrail on a model answer: no causal or forecast claims, evidence that checks out.

Everything the guardrail decides is deterministic and listed here.

Claims. ``FORBIDDEN_PHRASES`` are looked up, case-insensitive, at the start of a word (so
``forecast`` also finds ``forecasts``). A phrase in the text of a chart rejects the text of that
chart (``GUARDRAIL_REJECTED``) and no other chart. On the chart of the forecast of the service
the words of ``FORECAST_PHRASES`` are allowed, because the model may comment on that forecast;
promises, predictions of its own and causes stay forbidden there too.

Evidence. A text is kept only when its evidence names at least one number and every number it
names is found in the series of the chart (see ``evidence_is_in_series``); a text that writes a
number that is not in the series is not kept (see ``names_only_numbers_of``).

A 4-digit year written right after a month name ("April 2026", "from July 2024 to December 2026")
is a date and is not checked. The number of points of the series, and the two counts of a title
such as "latest 30 of 102 months", are figures of the series. Every other number is checked, also
one that stands beside a year.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.application.chart_series import ChartSeries

# Observed associations only: no cause, no promise, no prediction.
FORBIDDEN_PHRASES: tuple[str, ...] = (
    # cause
    "because",
    "caused by",
    "causes",
    "cause of",
    "leads to",
    "led to",
    "results in",
    "resulted in",
    "is responsible for",
    "as a result of",
    "thanks to",
    "due to",
    "driven by",
    # promise and prediction
    "will increase",
    "will decrease",
    "will rise",
    "will fall",
    "will grow",
    "will drop",
    "will reduce",
    "will improve",
    "will boost",
    "will lead",
    "will result",
    "guarantee",
    "forecast",
    "predict",
    "projected",
    "expected to",
    "going to",
    "in the future",
    "next year",
    "next month",
    "next quarter",
)
# The words that describe the forecast of the service; allowed on the chart of that forecast.
FORECAST_PHRASES: tuple[str, ...] = ("forecast", "projected", "next month")


def _phrase_pattern(phrases: Iterable[str]) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in phrases) + r")", re.IGNORECASE)


_FORBIDDEN = _phrase_pattern(FORBIDDEN_PHRASES)
_FORBIDDEN_ON_FORECAST = _phrase_pattern(p for p in FORBIDDEN_PHRASES if p not in FORECAST_PHRASES)
# A number as written in text: 1,234  22.3  -5  (not the digits inside a word such as Q3).
_NUMBER = re.compile(r"(?<![\w.])(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(\s*%)?")
# A year written after a month name ("April 2026", "Jul 2025") is a date, not a figure. The month
# name is case-sensitive so that the verb "may" does not hide a number.
_MONTH_YEAR = re.compile(
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November"
    r"|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?)\s+(?:19|20)\d{2}(?!\d|[.,]\d)"
)
# The title that chart_series gives a long monthly series: "(latest 30 of 102 months)".
_SHORTENED_TITLE = re.compile(r"latest (\d+) of (\d+) months")
# A share kept as a fraction (0.223 for 22.3) is accepted with at least this many decimals, so
# that a stray 0 or 1 does not match every share.
_FRACTION_DECIMALS = 2
_PERCENT = Decimal(100)


def makes_forbidden_claim(text: str, is_forecast_chart: bool = False) -> bool:
    """True for a cause, a promise or a prediction; the forecast of the service may be described."""
    pattern = _FORBIDDEN_ON_FORECAST if is_forecast_chart else _FORBIDDEN
    return pattern.search(text) is not None


@dataclass(frozen=True, slots=True)
class _Mention:
    value: Decimal
    decimals: int
    is_percent: bool


def _label_pattern(label: str) -> re.Pattern[str]:
    # A label such as "2" is not cut out of the middle of a number such as 32.3.
    return re.compile(r"(?<![\d.,])" + re.escape(label) + r"(?!\d|[.,]\d)")


def _mentions(text: str, labels: Iterable[str]) -> list[_Mention]:
    text = _MONTH_YEAR.sub(r"\1", text)
    # The digits of a group label ("2019-07", "0-30 days") are not figures of the model.
    for label in sorted(set(labels), key=len, reverse=True):
        if label:
            text = _label_pattern(label).sub(" ", text)
    found: list[_Mention] = []
    for match in _NUMBER.finditer(text):
        value = Decimal(match.group(1).replace(",", ""))
        found.append(_Mention(value, _decimals(value), bool(match.group(2))))
    return found


def _decimals(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def numbers_in(text: str) -> tuple[float, ...]:
    """The numbers written in ``text`` (dates after a month name left out)."""
    return tuple(float(m.value) for m in _mentions(text, ()))


def names_a_number(text: str) -> bool:
    return bool(_mentions(text, ()))


def _round(value: Decimal, decimals: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def _allowed_values(series: ChartSeries) -> list[Decimal]:
    values: list[Decimal] = []
    for point in series.points:
        for number in (point.value, point.numerator, point.denominator):
            if number is not None:
                values.append(Decimal(str(number)))
        values.extend(Decimal(str(n)) for n in (point.low, point.high) if n is not None)
    values.extend(Decimal(str(fact)) for fact in series.facts)
    # The number of points and the counts of the title ("latest 30 of 102 months") are stated too.
    if series.points:
        values.append(Decimal(len(series.points)))
    for count in _SHORTENED_TITLE.findall(series.title):
        values.extend(Decimal(n) for n in count)
    return values


def _matches(mention: _Mention, series: ChartSeries, allowed: list[Decimal]) -> bool:
    """The rule: the number as written equals a figure of the series rounded to as many decimals.

    22.3, 22.3% and 22 all name a share of 22.3 (22 is 22.3 rounded to no decimal). A share of a
    percent series may also be written as a fraction: 0.223, with at least two decimals and no
    percent sign. The numerators and denominators of the points count as figures of the series.
    """
    if any(_round(v, mention.decimals) == mention.value for v in allowed):
        return True
    is_fraction = (
        series.unit == "%"
        and not mention.is_percent
        and mention.decimals >= _FRACTION_DECIMALS
        and abs(mention.value) <= 1
    )
    if not is_fraction:
        return False
    return any(_round(v / _PERCENT, mention.decimals) == mention.value for v in allowed)


def evidence_is_in_series(evidence: str, series: ChartSeries) -> bool:
    """True when the evidence names numbers and every one of them is found in the series."""
    labels = [p.label for p in series.points] + [series.id, series.title]
    mentions = _mentions(evidence, labels)
    allowed = _allowed_values(series)
    return bool(mentions) and all(_matches(m, series, allowed) for m in mentions)


def names_only_numbers_of(text: str, series: ChartSeries) -> bool:
    """True when every number the text writes is found in the series (no number is fine)."""
    labels = [p.label for p in series.points] + [series.id, series.title]
    allowed = _allowed_values(series)
    return all(_matches(m, series, allowed) for m in _mentions(text, labels))
