"""The guardrail on a model answer: no causal or forecast claims, evidence that checks out.

Everything the guardrail decides is deterministic and listed here.

Claims. ``FORBIDDEN_PHRASES`` are looked up, case-insensitive, at the start of a word (so
``forecast`` also finds ``forecasts``). A phrase in the executive summary or in a suggestion or
its evidence rejects the whole insight (``GUARDRAIL_REJECTED``); in an observation it drops that
observation.

Evidence. A suggestion's evidence must name at least one number, else the suggestion is dropped.
An observation is kept only when its series is one of the charts of the analysis, its evidence
names at least one number, and every number it names is found in that series (see
``evidence_is_in_series``).
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
_FORBIDDEN = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in FORBIDDEN_PHRASES) + r")", re.IGNORECASE
)
# A number as written in text: 1,234  22.3  -5  (not the digits inside a word such as Q3).
_NUMBER = re.compile(r"(?<![\w.])(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(\s*%)?")
# A share kept as a fraction (0.223 for 22.3) is accepted with at least this many decimals, so
# that a stray 0 or 1 does not match every share.
_FRACTION_DECIMALS = 2
_PERCENT = Decimal(100)


def makes_forbidden_claim(text: str) -> bool:
    return _FORBIDDEN.search(text) is not None


@dataclass(frozen=True, slots=True)
class _Mention:
    value: Decimal
    decimals: int
    is_percent: bool


def _label_pattern(label: str) -> re.Pattern[str]:
    # A label such as "2" is not cut out of the middle of a number such as 32.3.
    return re.compile(r"(?<![\d.,])" + re.escape(label) + r"(?!\d|[.,]\d)")


def _mentions(text: str, labels: Iterable[str]) -> list[_Mention]:
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
