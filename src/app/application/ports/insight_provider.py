"""Port: the AI insight of an analysis."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from app.application.documents import JsonObject


class InsightProvider(Protocol):
    def info(self) -> dict[str, str]:
        """``provider``, ``model`` and ``prompt_version`` for the result; empty if none."""
        ...

    def insight_for(self, name: str, analysis: JsonObject) -> JsonObject:
        """The ``Insight`` of the contract for the analysis ``name``; never raises.

        ``analysis`` may carry a ``forecast``: the part of the forecast of the service that
        belongs to it (see ``forecast_for_analysis``); it is not part of the stored analysis.
        """
        ...

    def overall_for(
        self, analyses: Mapping[str, JsonObject], forecast: JsonObject
    ) -> JsonObject | None:
        """The overall interpretation (``insights.overall`` of the contract), or None; never raises.

        ``analyses`` carry their insight. None means no AI text is kept (nothing to read, a
        rejected or failed answer); the caller then writes the fallback from the figures.
        """
        ...
