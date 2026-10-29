"""The AI insight of an analysis, asked from a model and checked by the guardrail."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from app.application.chart_series import ChartSeries, chart_series
from app.application.documents import JsonObject
from app.application.insight_answer import ANSWER_SCHEMA, Answer, parse_answer
from app.application.insight_guardrail import (
    evidence_is_in_series,
    makes_forbidden_claim,
    names_a_number,
)
from app.application.insight_prompt import (
    PROMPT_VERSION,
    RETRY_REMINDER,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.application.ports.model_client import (
    ModelClient,
    ModelFailedError,
    ModelRequest,
    ModelTimeoutError,
    TimeLimits,
)

logger = logging.getLogger(__name__)

AI_LABEL = "AI-generated"
TIMEOUT = "TIMEOUT"
BAD_STRUCTURE = "BAD_STRUCTURE"
GUARDRAIL_REJECTED = "GUARDRAIL_REJECTED"
MODEL_ERROR = "MODEL_ERROR"
ANALYSIS_UNAVAILABLE = "ANALYSIS_UNAVAILABLE"
_ATTEMPTS = 2  # the request and one retry on a bad structure

Clock = Callable[[], datetime]


class _UnavailableError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ModelInsightProvider:
    """Gives each analysis one request to the model; the requests are made one after the other."""

    def __init__(
        self,
        client: ModelClient,
        limits: TimeLimits,
        max_output_tokens: int,
        clock: Clock,
    ) -> None:
        self._client = client
        self._limits = limits
        self._max_output_tokens = max_output_tokens
        self._clock = clock

    def info(self) -> dict[str, str]:
        return {
            "provider": self._client.provider,
            "model": self._client.model,
            "prompt_version": PROMPT_VERSION,
        }

    def insight_for(self, name: str, analysis: JsonObject) -> JsonObject:
        """Never raises: any failure is an unavailable insight with a stable reason."""
        try:
            return self._available(name, analysis)
        except _UnavailableError as unavailable:
            return self._unavailable(unavailable.reason)
        except Exception:
            # The run goes on with the next analysis whatever went wrong here.
            logger.exception("insight of analysis %s failed", name)
            return self._unavailable(MODEL_ERROR)

    def _unavailable(self, reason: str) -> JsonObject:
        return {
            "status": "unavailable",
            "reason": reason,
            "provider": self._client.provider,
            "model": self._client.model,
        }

    def _available(self, name: str, analysis: JsonObject) -> JsonObject:
        if analysis.get("status") != "available":
            raise _UnavailableError(ANALYSIS_UNAVAILABLE)
        charts = chart_series(analysis.get("findings") or {})
        answer = self._ask(build_user_prompt(name, analysis, charts))
        return self._checked(answer, charts)

    def _ask(self, prompt: str) -> Answer:
        user = prompt
        for _ in range(_ATTEMPTS):
            text = self._generate(user)
            if not text.strip():
                raise _UnavailableError(MODEL_ERROR)
            answer = parse_answer(text)
            if answer is not None:
                return answer
            user = f"{prompt}\n\n{RETRY_REMINDER}"
        raise _UnavailableError(BAD_STRUCTURE)

    def _generate(self, user: str) -> str:
        request = ModelRequest(
            SYSTEM_PROMPT, user, ANSWER_SCHEMA, self._max_output_tokens, self._limits
        )
        try:
            return self._client.generate(request)
        except ModelTimeoutError:
            raise _UnavailableError(TIMEOUT) from None
        except ModelFailedError as failure:
            logger.warning("the model request failed: %s", failure)
            raise _UnavailableError(MODEL_ERROR) from None

    def _checked(self, answer: Answer, charts: list[ChartSeries]) -> JsonObject:
        suggestions = [
            {"suggestion": s.suggestion, "evidence": s.evidence, "sample_size": s.sample_size}
            for s in answer.suggestions
            if names_a_number(s.evidence)
        ]
        claims = [answer.executive_summary]
        claims += [f"{s['suggestion']} {s['evidence']}" for s in suggestions]
        if not answer.executive_summary.strip() or any(makes_forbidden_claim(c) for c in claims):
            raise _UnavailableError(GUARDRAIL_REJECTED)
        return {
            "status": "available",
            "reason": None,
            "label": AI_LABEL,
            "provider": self._client.provider,
            "model": self._client.model,
            "generated_at": self._clock().isoformat(),
            "executive_summary": answer.executive_summary.strip(),
            "improvement_suggestions": suggestions,
            "observations": _kept_observations(answer, charts),
        }


def _kept_observations(answer: Answer, charts: list[ChartSeries]) -> list[JsonObject]:
    """One observation per chart: the first that names only numbers of its series."""
    by_id = {c.id: c for c in charts}
    kept: dict[str, JsonObject] = {}
    for item in answer.observations:
        series = by_id.get(item.series)
        if series is None or item.series in kept:
            continue
        if makes_forbidden_claim(f"{item.text} {item.evidence}"):
            continue
        if not evidence_is_in_series(item.evidence, series):
            continue
        kept[item.series] = {"series": item.series, "text": item.text, "evidence": item.evidence}
    return list(kept.values())
