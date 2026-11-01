"""The overall interpretation of a run: its input, the series that checks it, and the fallback.

The input of the model is text: the summary and the recommendations of every analysis that has an
AI insight, the largest finding of every available analysis, and the figures of the forecast of
the service. The numbers the model may cite are the
numbers written in that text (see ``figures_of_input``); the guardrail is the one of the charts.
When there is no AI text, ``figures_overall`` writes a short text from the largest finding of
each analysis, and the result says ``source: figures``.
"""

from __future__ import annotations

import json
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


def _name(analysis_name: str) -> str:
    text = analysis_name.replace("_", " ")
    return text[:1].upper() + text[1:]


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _insight_lines(name: str, insight: JsonObject) -> list[str]:
    lines = [f"Analysis {name}:", f"Summary: {insight.get('executive_summary') or ''}"]
    for suggestion in insight.get("improvement_suggestions") or []:
        lines.append(f"Recommendation: {suggestion['suggestion']} ({suggestion['evidence']})")
    return lines


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


def _largest_lines(analyses: Mapping[str, JsonObject]) -> list[str]:
    return [
        f"Largest finding of {_name(name)}: {line}"
        for name, analysis in analyses.items()
        if analysis.get("status") == AVAILABLE and (line := _largest(analysis)) is not None
    ]


def overall_input(
    insights: Mapping[str, JsonObject], forecast: JsonObject, analyses: Mapping[str, JsonObject]
) -> str:
    """The text the model reads: the texts of the analyses, the largest finding of every available
    analysis and the forecast, not the bookings. The figures of the findings are allowed numbers.
    """
    lines: list[str] = []
    for name, insight in insights.items():
        lines.extend(_insight_lines(name, insight))
    lines.extend(_largest_lines(analyses))
    lines.extend(_forecast_lines(forecast))
    return "\n".join(lines)


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
