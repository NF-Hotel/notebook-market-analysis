"""Port: the texts of the price suggestions (an explanation of each, and ideas without a price)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.application.documents import JsonObject
from app.domain.analyses.price_suggestions import PriceSuggestion


class PriceTextProvider(Protocol):
    def explain(self, suggestion: PriceSuggestion) -> JsonObject:
        """``{"text", "ai_written"}``; never raises, and never changes the suggestion."""
        ...

    def ideas(self, suggestions: Sequence[PriceSuggestion]) -> list[JsonObject]:
        """Up to three ideas without a price; empty when there is no AI; never raises."""
        ...
