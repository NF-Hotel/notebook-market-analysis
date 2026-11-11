"""The ``price_suggestions`` of the result document (result schema 1.3)."""

from __future__ import annotations

from app.application.documents import JsonObject
from app.application.ports.price_text_provider import PriceTextProvider
from app.domain.analyses.price_suggestions import (
    NotEnoughHistory,
    PriceSuggestion,
    PriceSuggestionSet,
)


def _suggestion(suggestion: PriceSuggestion, texts: PriceTextProvider) -> JsonObject:
    body: JsonObject = {
        "room_size": suggestion.room_size,
        "first_date": suggestion.first_date.isoformat(),
        "last_date": suggestion.last_date.isoformat(),
        "change": suggestion.change,
        "percent": float(suggestion.percent),
        "reason": suggestion.reason,
        "threshold": float(suggestion.threshold),
        "history": [
            {"year": year.year, "occupancy": year.occupancy} for year in suggestion.history
        ],
        "explanation": texts.explain(suggestion),
    }
    if suggestion.holiday is not None:
        body["holiday"] = suggestion.holiday
    return body


def _missing(item: NotEnoughHistory) -> JsonObject:
    body: JsonObject = {
        "first_date": item.first_date.isoformat(),
        "last_date": item.last_date.isoformat(),
        "years_found": item.years_found,
    }
    if item.holiday is not None:
        body["holiday"] = item.holiday
    return body


def price_suggestions_document(found: PriceSuggestionSet, texts: PriceTextProvider) -> JsonObject:
    """The suggestions of the rule with their texts; the texts change none of the figures."""
    return {
        "as_of": found.as_of.isoformat(),
        "horizon_end": found.horizon_end.isoformat(),
        "formula": found.formula,
        "limitations": list(found.limitations),
        "suggestions": [_suggestion(s, texts) for s in found.suggestions],
        "not_enough_history": [_missing(m) for m in found.not_enough_history],
        "ideas": texts.ideas(found.suggestions),
    }
