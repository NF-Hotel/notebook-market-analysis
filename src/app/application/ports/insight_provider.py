"""Port: the AI insight of an analysis."""

from __future__ import annotations

from typing import Protocol

from app.application.documents import JsonObject


class InsightProvider(Protocol):
    def info(self) -> dict[str, str]:
        """``provider``, ``model`` and ``prompt_version`` for the result; empty if none."""
        ...

    def insight_for(self, name: str, analysis: JsonObject) -> JsonObject:
        """The ``Insight`` of the contract for the analysis ``name``; never raises."""
        ...
