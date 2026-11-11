"""The AI text of the price suggestions: an explanation of each and ideas without a price.

The AI never sets a price, a percentage or a date: the rule has decided them. The model only
explains, and a text that names a number or a month that is not the suggestion's own, a currency,
a cause or a promise is rejected. A rejected or failed answer gives the text built from the
figures, which is marked ``ai_written: false``. Ideas carry no number at all.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.application.documents import JsonObject
from app.application.insight_answer import strip_html
from app.application.insight_guardrail import forbidden_phrase_in, names_a_number, numbers_in
from app.application.ports.model_client import (
    ModelClient,
    ModelFailedError,
    ModelRequest,
    ModelTimeoutError,
    TimeLimits,
)
from app.domain.analyses.price_suggestions import PriceSuggestion

logger = logging.getLogger(__name__)

MAX_IDEAS = 3
_REQUESTS = 2  # the request and one more that names the rule the first answer broke
_TEXT_SCHEMA: JsonObject = {
    "type": "object",
    "required": ["text"],
    "additionalProperties": False,
    "properties": {"text": {"type": "string"}},
}
_IDEAS_SCHEMA: JsonObject = {
    "type": "object",
    "required": ["ideas"],
    "additionalProperties": False,
    "properties": {"ideas": {"type": "array", "maxItems": MAX_IDEAS, "items": {"type": "string"}}},
}
EXPLAIN_SYSTEM_PROMPT = (
    "You explain one room price suggestion to a hotel manager in one or two plain sentences. "
    "The suggestion was decided by a fixed rule; you only say why, using the figures you are "
    "given. Use no other number, no currency, no price, and name no month or date other than "
    "the ones given. Do not say what will happen and do not give a cause."
)
IDEAS_SYSTEM_PROMPT = (
    "You give a hotel manager up to three short ideas for the quiet and the busy periods that "
    "are listed, such as a package or a minimum stay. Write no number, no price, no percentage "
    "and no date, do not say what will happen and do not give a cause. One sentence each."
)
_CURRENCY = re.compile(r"[$€£]|\b(?:kr|dkk|eur|usd|euros?|kroner|dollars?)\b", re.IGNORECASE)
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_NAME = re.compile(r"\b(" + "|".join(_MONTHS) + r")\b")
_ONE_PLACE = Decimal("0.1")


def _percent(share: float) -> Decimal:
    return (Decimal(str(share)) * 100).quantize(_ONE_PLACE, rounding=ROUND_HALF_UP)


def _percent_text(share: float) -> str:
    return f"{_percent(share):f}".removesuffix(".0")


def _period(suggestion: PriceSuggestion) -> str:
    first, last = suggestion.first_date, suggestion.last_date
    name = suggestion.holiday
    if first == last:
        return f"{name} ({first.isoformat()})" if name else first.isoformat()
    return f"{first.isoformat()} to {last.isoformat()}"


def fallback_text(suggestion: PriceSuggestion) -> JsonObject:
    """The explanation built from the figures; not written by an AI."""
    years = ", ".join(
        f"{year.year}: {_percent_text(year.occupancy)} %" for year in suggestion.history
    )
    threshold = _percent_text(float(suggestion.threshold))
    direction = "at or above" if suggestion.change == "surcharge" else "at or below"
    text = (
        f"The occupancy of the same days in earlier years was {direction} {threshold} % "
        f"({years}), so the rule suggests a {suggestion.change} of {suggestion.percent} % "
        f"for {_period(suggestion)}."
    )
    return {"text": text, "ai_written": False}


def allowed_numbers(suggestion: PriceSuggestion) -> set[Decimal]:
    """The numbers an explanation of the suggestion may write: its own percentages, dates, years."""
    allowed: set[Decimal] = {Decimal(suggestion.percent), Decimal(suggestion.threshold) * 100}
    for day in (suggestion.first_date, suggestion.last_date):
        allowed.update({Decimal(day.year), Decimal(day.month), Decimal(day.day)})
    for year in suggestion.history:
        allowed.add(Decimal(year.year))
        share = Decimal(str(year.occupancy)) * 100
        allowed.update({share.quantize(Decimal(1), ROUND_HALF_UP), _percent(year.occupancy)})
        allowed.update({Decimal(year.taken), Decimal(year.capacity)})
    return {value.normalize() for value in allowed}


def broken_rule(text: str, suggestion: PriceSuggestion) -> str | None:
    """What an explanation breaks, in words for the next request; None when it is kept."""
    if (claim := forbidden_phrase_in(text)) is not None:
        return f"it makes a claim that is not allowed: {claim}"
    if (currency := _CURRENCY.search(text)) is not None:
        return f'it names a currency or a price: "{currency.group()}"'
    allowed = allowed_numbers(suggestion)
    for number in numbers_in(text):
        if Decimal(str(number)).normalize() not in allowed:
            return f"it writes the number {number:g}, which is not one of the figures given"
    months = {suggestion.first_date.month, suggestion.last_date.month}
    for name in _MONTH_NAME.findall(text):
        if _MONTHS.index(name) + 1 not in months:
            return f'it names the month "{name}", which is not in the period'
    return None


def broken_idea_rule(text: str) -> str | None:
    """What an idea breaks: any number, a currency, a cause or a promise."""
    if names_a_number(text) or re.search(r"\d", text):
        return "it contains a number"
    if _CURRENCY.search(text) is not None:
        return "it names a currency or a price"
    if (claim := forbidden_phrase_in(text)) is not None:
        return f"it makes a claim that is not allowed: {claim}"
    return None


def _facts(suggestion: PriceSuggestion) -> str:
    history = [
        {"year": y.year, "occupancy_percent": _percent_text(y.occupancy)}
        for y in suggestion.history
    ]
    return json.dumps(
        {
            "change": suggestion.change,
            "percent": suggestion.percent,
            "period": _period(suggestion),
            "room_size": suggestion.room_size,
            "reason": suggestion.reason,
            "threshold_percent": _percent_text(float(suggestion.threshold)),
            "earlier_years": history,
        },
        ensure_ascii=False,
    )


class PriceExplainer:
    """Asks the model for the texts of the suggestions; with no model it gives the fallback."""

    def __init__(
        self, client: ModelClient | None, limits: TimeLimits, max_output_tokens: int
    ) -> None:
        self._client = client
        self._limits = limits
        self._max_output_tokens = max_output_tokens

    def explain(self, suggestion: PriceSuggestion) -> JsonObject:
        """``{"text", "ai_written"}``; never raises."""
        if self._client is None:
            return fallback_text(suggestion)
        reminder = ""
        for _ in range(_REQUESTS):
            answer = self._ask(
                EXPLAIN_SYSTEM_PROMPT, f"Suggestion: {_facts(suggestion)}{reminder}", _TEXT_SCHEMA
            )
            text = strip_html(str(answer.get("text", ""))).strip() if answer else ""
            if not text:
                break
            rule = broken_rule(text, suggestion)
            if rule is None:
                return {"text": text, "ai_written": True}
            reminder = (
                f"\nYour last answer was rejected because {rule}. Write it again without that."
            )
        return fallback_text(suggestion)

    def ideas(self, suggestions: Sequence[PriceSuggestion]) -> list[JsonObject]:
        """Up to three ideas without a price, each marked ``ai_written``; never raises."""
        if self._client is None or not suggestions:
            return []
        periods = "; ".join(
            sorted({f"{s.change} {s.reason.replace('_', ' ')}" for s in suggestions})
        )
        answer = self._ask(IDEAS_SYSTEM_PROMPT, f"Periods: {periods}", _IDEAS_SCHEMA)
        raw = answer.get("ideas") if answer else None
        if not isinstance(raw, list):
            return []
        kept = []
        for item in raw:
            text = strip_html(str(item)).strip()
            if text and broken_idea_rule(text) is None:
                kept.append({"text": text, "ai_written": True})
        return kept[:MAX_IDEAS]

    def _ask(self, system: str, user: str, schema: JsonObject) -> JsonObject | None:
        if self._client is None:
            return None
        request = ModelRequest(system, user, schema, self._max_output_tokens, self._limits)
        try:
            parsed = json.loads(self._client.generate(request))
        except (ModelTimeoutError, ModelFailedError, json.JSONDecodeError) as error:
            logger.warning("price explanation request failed: %s", error)
            return None
        return parsed if isinstance(parsed, dict) else None
