"""The insight used until an AI provider is configured."""

from __future__ import annotations

from app.application.documents import JsonObject

AI_NOT_CONFIGURED = "AI_NOT_CONFIGURED"


class UnconfiguredInsightProvider:
    """Gives every analysis an unavailable insight; it calls no model."""

    def info(self) -> dict[str, str]:
        return {}

    def insight_for(self, name: str, analysis: JsonObject) -> JsonObject:
        return {"status": "unavailable", "reason": AI_NOT_CONFIGURED}
