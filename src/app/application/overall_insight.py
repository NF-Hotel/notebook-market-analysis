"""The overall interpretation of a run: its input, the series that checks it, and the fallback.

The input of the model is a short text: for every available analysis the first sentence of its
summary and its largest finding, and the figures of the forecast of the service. The numbers the
model may cite are the numbers written in that text (see ``figures_of_input``); the guardrail is
the one of the charts.
When there is no AI text, ``figures_overall`` writes a short text from the largest finding of
each analysis, and the result says ``source: figures``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from app.application.chart_series import ChartSeries, chart_series
from app.application.documents import JsonObject
from app.application.insight_guardrail import numbers_in

AVAILABLE = "available"
SOURCE_AI = "ai"
SOURCE_FIGURES = "figures"
FIGURES_LABEL = "Calculated from the figures"
OVERALL_SERIES_ID = "overall"
NO_FIGURES = "There are no figures to summarise."
# The input has to fit the context window of a small local model with room for the answer.
MAX_OVERALL_INPUT_CHARS = 4000
MIN_SENTENCE_CHARS = 20
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _name(analysis_name: str) -> str:
    text = analysis_name.replace("_", " ")
    return text[:1].upper() + text[1:]


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _forecast_lines(forecast: JsonObject) -> list[str]:
    measures = forecast.get("measures") or {}
    lines = [f"Forecast of the service, months of history: {forecast.get('history_months')}"]
    for measure, data in measures.items():
        months = [[m["group"], m["value"], m["low"], m["high"]] for m in data.get("months", [])]
        lines.append(f"Forecast {measure} ({data.get('unit')}): {_compact(months)}")
    return lines


def available_insights(analyses: Mapping[str, JsonObject]) -> dict[str, JsonObject]:
    """The insights of the analyses that have text, by analysis name."""
    return {
        name: analysis["insight"]
        for name, analysis in analyses.items()
        if (analysis.get("insight") or {}).get("status") == AVAILABLE
    }


def _plain(markdown: str) -> str:
    """The first sentence of a Markdown text as plain text: no heading, list sign or bold."""
    for line in markdown.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        text = " ".join(text.lstrip("-*+ ").replace("**", "").split())
        return _SENTENCE_END.split(text, maxsplit=1)[0]
    return ""


def _shorten(sentence: str, limit: int) -> str:
    """The sentence cut at a word boundary to at most ``limit`` characters."""
    if len(sentence) <= limit:
        return sentence
    head = sentence[:limit]
    return (head.rsplit(" ", maxsplit=1)[0] if " " in head else head).rstrip(",;:- ")


def _entries(
    insights: Mapping[str, JsonObject], analyses: Mapping[str, JsonObject]
) -> list[tuple[str, str, str | None]]:
    """For each available analysis: its label, the first sentence of its summary, its largest."""
    entries: list[tuple[str, str, str | None]] = []
    for name, analysis in analyses.items():
        insight = insights.get(name)
        largest = _largest(analysis) if analysis.get("status") == AVAILABLE else None
        if insight is None and largest is None:
            continue
        sentence = _plain(str((insight or {}).get("executive_summary") or ""))
        label = f"Largest finding of {_name(name)}: {largest}" if largest else None
        entries.append((f"Analysis {_name(name)}:", sentence, label))
    return entries


def _text(entries: list[tuple[str, str, str | None]], forecast: list[str], limit: int) -> str:
    lines: list[str] = []
    for head, sentence, largest in entries:
        lines.append(f"{head} {_shorten(sentence, limit)}".rstrip())
        if largest:
            lines.append(largest)
    return "\n".join([*lines, *forecast])


def overall_input(
    insights: Mapping[str, JsonObject], forecast: JsonObject, analyses: Mapping[str, JsonObject]
) -> str:
    """The compact text the model reads, at most ``MAX_OVERALL_INPUT_CHARS`` characters.

    For every available analysis: its name, the first sentence of its summary and its largest
    finding; then the forecast. Recommendations and the rest of the texts are left out. When the
    text is too long the sentences are shortened evenly; no analysis is dropped. The figures
    written in it are the allowed numbers (see ``figures_of_input``).
    """
    entries = _entries(insights, analyses)
    forecast_lines = _forecast_lines(forecast)
    limit = max((len(sentence) for _, sentence, _ in entries), default=0)
    text = _text(entries, forecast_lines, limit)
    while len(text) > MAX_OVERALL_INPUT_CHARS and limit > MIN_SENTENCE_CHARS:
        limit -= 10
        text = _text(entries, forecast_lines, limit)
    return text


def figures_of_input(text: str) -> ChartSeries:
    """The input as one series whose figures are the numbers written in it."""
    return ChartSeries(
        OVERALL_SERIES_ID, "Overall", "", (), facts=numbers_in(text), is_forecast=True
    )


def _largest(analysis: JsonObject) -> str | None:
    charts = chart_series(analysis.get("findings") or {})
    if not charts:
        return None
    chart = charts[0]
    if not chart.points:
        return None
    top = max(chart.points, key=lambda point: point.value)
    value = f"{top.value:.1f}".removesuffix(".0")
    unit = chart.unit if chart.unit == "%" else f" {chart.unit}" if chart.unit else ""
    return f"{chart.title}: {top.label} is the largest at {value}{unit}"


def figures_overall(analyses: Mapping[str, JsonObject]) -> JsonObject:
    """A short overall text from the largest finding of each available analysis."""
    items = [
        f"- **{_name(name)}**: {line}."
        for name, analysis in analyses.items()
        if analysis.get("status") == AVAILABLE and (line := _largest(analysis)) is not None
    ]
    text = "\n".join(["**Key figures**", "", *items]) if items else NO_FIGURES
    return {
        "status": AVAILABLE,
        "source": SOURCE_FIGURES,
        "label": FIGURES_LABEL,
        "text": text,
    }
