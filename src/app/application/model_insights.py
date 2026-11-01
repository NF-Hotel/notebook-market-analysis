"""The AI insight of an analysis: one request to the model for each chart, checked by the guardrail.

A chart whose text is rejected, or whose answer is bad, loses only its own text; the other charts
of the analysis keep theirs. The insight of an analysis is unavailable only when no chart has text.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.application.chart_series import ChartSeries, chart_series
from app.application.documents import JsonObject
from app.application.forecast_charts import FORECAST_KEY, forecast_chart
from app.application.insight_answer import (
    ANSWER_SCHEMA,
    MAX_OVERALL_RECOMMENDATIONS,
    MAX_RECOMMENDATIONS,
    Answer,
    Suggestion,
    parse_answer,
)
from app.application.insight_guardrail import (
    evidence_is_in_series,
    makes_forbidden_claim,
    names_a_number,
    names_only_numbers_of,
)
from app.application.insight_prompt import (
    OVERALL_SYSTEM_PROMPT,
    PROMPT_VERSION,
    RETRY_REMINDER,
    RULES_REMINDER,
    SYSTEM_PROMPT,
    build_overall_prompt,
    build_user_prompt,
)
from app.application.overall_insight import (
    AVAILABLE,
    SOURCE_AI,
    available_insights,
    figures_of_input,
    overall_input,
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
# A model that timed out or failed is not asked again for the rest of the analysis.
_STOPS_THE_ANALYSIS = frozenset({TIMEOUT, MODEL_ERROR})

Clock = Callable[[], datetime]


class _UnavailableError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ModelInsightProvider:
    """Gives each chart of an analysis one request; the requests are made one after the other."""

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
        charts = _charts_of(analysis)
        # An analysis without a chart is asked once, about its findings as a whole.
        texts, reason = self._read_all(name, analysis, charts or [None])
        if not texts:
            raise _UnavailableError(reason or MODEL_ERROR)
        return {
            "status": "available",
            "reason": None,
            "label": AI_LABEL,
            "provider": self._client.provider,
            "model": self._client.model,
            "generated_at": self._clock().isoformat(),
            "executive_summary": _as_markdown(texts),
            "improvement_suggestions": [s for t in texts for s in t.suggestions],
            "observations": [t.observation for t in texts if t.series is not None],
        }

    def _read_all(
        self, name: str, analysis: JsonObject, charts: Sequence[ChartSeries | None]
    ) -> tuple[list[_ChartText], str | None]:
        """The text of each chart that has one, and the reason the first other chart has none."""
        texts: list[_ChartText] = []
        reason: str | None = None
        for chart in charts:
            try:
                texts.append(self._read(name, analysis, chart))
            except _UnavailableError as failure:
                logger.info("no insight text for a chart of %s: %s", name, failure.reason)
                reason = reason or failure.reason
                if failure.reason in _STOPS_THE_ANALYSIS:
                    break
        return texts, reason

    def _read(self, name: str, analysis: JsonObject, chart: ChartSeries | None) -> _ChartText:
        prompt = build_user_prompt(name, analysis, chart)
        try:
            return self._asked_twice(prompt, SYSTEM_PROMPT, True, lambda a: _checked(a, chart))
        except _UnavailableError:
            raise
        except Exception:
            # The rest of the analysis is not asked after a failure nobody expected.
            logger.exception("insight of a chart of analysis %s failed", name)
            raise _UnavailableError(MODEL_ERROR) from None

    def overall_for(
        self, analyses: Mapping[str, JsonObject], forecast: JsonObject
    ) -> JsonObject | None:
        """One more request: the overall interpretation, or None when there is none to keep.

        It reads the texts of the analyses and the forecast, never the bookings, and it never
        raises. A rejected or failed answer leaves the analyses as they are.
        """
        insights = available_insights(analyses)
        if not insights:
            return None
        text = overall_input(insights, forecast, analyses)
        try:
            # The figures of the input are a forecast-flagged series: the overall text may
            # describe the forecast of the service, and nothing else is let through.
            figures = figures_of_input(text)
            return self._overall(
                self._asked_twice(
                    build_overall_prompt(text),
                    OVERALL_SYSTEM_PROMPT,
                    False,
                    lambda a: _checked(a, figures, MAX_OVERALL_RECOMMENDATIONS),
                )
            )
        except _UnavailableError as failure:
            logger.info("no overall interpretation: %s", failure.reason)
        except Exception:
            logger.exception("the overall interpretation failed")
        return None

    def _asked_twice(
        self, prompt: str, system: str, plain: bool, check: Callable[[Answer], _ChartText]
    ) -> _ChartText:
        """The checked text; a rejected answer is asked once more with the rules, then it stands."""
        try:
            return check(self._ask(prompt, system, plain=plain))
        except _UnavailableError as rejected:
            if rejected.reason != GUARDRAIL_REJECTED:
                raise
        logger.info("an answer was rejected by the guardrail; asking once more")
        return check(self._ask(f"{prompt}\n\n{RULES_REMINDER}", system, plain=plain))

    def _overall(self, text: _ChartText) -> JsonObject:
        return {
            "status": AVAILABLE,
            "source": SOURCE_AI,
            "label": AI_LABEL,
            "generated_at": self._clock().isoformat(),
            "text": text.summary,
            "evidence": text.evidence,
            "recommendations": [
                {k: v for k, v in s.items() if k != "series"} for s in text.suggestions
            ],
        }

    def _ask(self, prompt: str, system: str = SYSTEM_PROMPT, *, plain: bool = True) -> Answer:
        user = prompt
        for _ in range(_ATTEMPTS):
            text = self._generate(user, system)
            if not text.strip():
                raise _UnavailableError(MODEL_ERROR)
            answer = parse_answer(text, plain=plain)
            if answer is not None:
                return answer
            user = f"{prompt}\n\n{RETRY_REMINDER}"
        raise _UnavailableError(BAD_STRUCTURE)

    def _generate(self, user: str, system: str) -> str:
        request = ModelRequest(system, user, ANSWER_SCHEMA, self._max_output_tokens, self._limits)
        try:
            return self._client.generate(request)
        except ModelTimeoutError:
            raise _UnavailableError(TIMEOUT) from None
        except ModelFailedError as failure:
            logger.warning("the model request failed: %s", failure)
            raise _UnavailableError(MODEL_ERROR) from None


@dataclass(frozen=True, slots=True)
class _ChartText:
    """What the model wrote about one chart, after the guardrail; ``series`` is None without one."""

    series: str | None
    title: str
    summary: str
    evidence: str
    suggestions: list[JsonObject]

    @property
    def observation(self) -> JsonObject:
        return {"series": self.series, "text": self.summary, "evidence": self.evidence}


def _as_markdown(texts: Sequence[_ChartText]) -> str:
    """One list item for each chart, naming the chart in bold; a text with no chart stands alone."""
    items = []
    for text in texts:
        body = text.summary.replace("\n", "\n  ")
        items.append(body if text.series is None else f"- **{text.title}**: {body}")
    return "\n".join(items)


def _charts_of(analysis: JsonObject) -> list[ChartSeries]:
    charts = chart_series(analysis.get("findings") or {})
    forecast = analysis.get(FORECAST_KEY)
    chart = forecast_chart(forecast) if isinstance(forecast, dict) else None
    return [*charts, chart] if chart is not None else charts


def _evidence_checks_out(evidence: str, chart: ChartSeries | None) -> bool:
    if chart is None:
        return names_a_number(evidence)
    return evidence_is_in_series(evidence, chart)


def _writes_only_known_numbers(text: str, chart: ChartSeries | None) -> bool:
    return chart is None or names_only_numbers_of(text, chart)


def _keeps(suggestion: Suggestion, chart: ChartSeries | None) -> bool:
    return _evidence_checks_out(suggestion.evidence, chart) and _writes_only_known_numbers(
        suggestion.suggestion, chart
    )


def _checked(
    answer: Answer, chart: ChartSeries | None, limit: int = MAX_RECOMMENDATIONS
) -> _ChartText:
    """The text of the chart, or ``GUARDRAIL_REJECTED`` for the chart."""
    series = None if chart is None else chart.id
    is_forecast = chart is not None and chart.is_forecast
    summary = answer.summary.strip()
    recommended = list(answer.suggestions[:limit])
    claims = [summary, answer.evidence, *(f"{s.suggestion} {s.evidence}" for s in recommended)]
    if (
        not summary
        or any(makes_forbidden_claim(c, is_forecast) for c in claims)
        or not _evidence_checks_out(answer.evidence, chart)
        or not _writes_only_known_numbers(summary, chart)
    ):
        raise _UnavailableError(GUARDRAIL_REJECTED)
    suggestions: list[JsonObject] = [
        {
            "suggestion": s.suggestion,
            "evidence": s.evidence,
            "sample_size": s.sample_size,
            **({"series": series} if series is not None else {}),
        }
        for s in recommended
        if _keeps(s, chart)
    ]
    return _ChartText(
        series, "" if chart is None else chart.title, summary, answer.evidence, suggestions
    )
