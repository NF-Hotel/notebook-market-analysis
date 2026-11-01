"""The prompt of one chart: what the model is told and what figures it is given."""

from __future__ import annotations

import json

from app.application.chart_series import ChartSeries
from app.application.documents import JsonObject
from app.application.insight_answer import MAX_OVERALL_RECOMMENDATIONS, MAX_RECOMMENDATIONS

PROMPT_VERSION = "4"
# The line that holds the chart; the fake model of the tests reads it. It is a list of the one
# chart, and an empty list for an analysis that has no chart.
CHARTS_PREFIX = "CHARTS: "

SYSTEM_PROMPT = f"""\
You are a careful data analyst for a hotel. You are given one chart of an analysis of the \
bookings, with its figures, and you write, in English, about that chart only: a summary in \
Markdown and one to {MAX_RECOMMENDATIONS} recommendations.

Rules:
- Describe observed associations only. Do not claim a cause (no "because", "due to", \
"caused by", "leads to") and do not promise or predict anything yourself (no "will increase", \
"guarantee", "expected to").
- "summary": two or three plain sentences that say what the chart shows. Use bold only for key \
figures (for example "**24.7%**"). Write no list, no heading, no table and no HTML. Name the \
numbers the text rests on, copied from the chart.
- "evidence": the numbers of the summary, copied from the chart (for example 22.3 or 22.3%).
- "recommendations": each has "suggestion" (what the hotel can look at or consider; Markdown, \
no HTML), "evidence" (the numbers of the chart it rests on) and "sample_size" (the number of \
bookings behind them, 0 if unknown).
- Use only numbers that are in the chart. Do not invent any and do not calculate new ones.
- A chart whose id starts with "forecast." is the forecast that the service calculated from the \
seasonal pattern of the history; its columns are the month, the expected value and the low and \
high of the band. You may describe it and cite its figures, and say so when the history is too \
short. Do not make a forecast of your own and do not promise that it will come true.
- Answer with one JSON object of the given schema and nothing else.
"""

RETRY_REMINDER = (
    "Your previous answer was not valid JSON of the required schema. Answer again with only "
    "one JSON object with the keys summary (string), evidence (string) and recommendations "
    "(list of objects with suggestion, evidence, sample_size)."
)

# Added to the request of a chart once, after the guardrail rejected the first answer.
RULES_REMINDER = (
    "Your previous answer was rejected by the checks of the service. Answer again and keep to "
    "the rules: describe observed associations only, with no cause, no promise and no "
    "prediction; use only numbers that are in the chart; write the summary as plain sentences."
)


OVERALL_SYSTEM_PROMPT = f"""\
You are a careful data analyst for a hotel. You are given the summaries and the \
recommendations that were written for each analysis of the bookings, the largest finding of \
each analysis, and the figures of the forecast of the service. Cover every analysis, not only \
the one with the most text. You write, in English, one overall interpretation of all of them.

Rules:
- Answer in Markdown, no HTML, no numbered list (use "-" for list items). "summary" holds, in \
this order: a heading "Key points" and a list of the key points; a heading \
"What it means together" and a short paragraph; a heading "Caveats" and a list of what the \
figures cannot say.
- "recommendations": 2 to {MAX_OVERALL_RECOMMENDATIONS} items, each with "suggestion", \
"evidence" and "sample_size" (0 if unknown).
- Describe observed associations only. Do not claim a cause (no "because", "due to", \
"caused by", "leads to") and do not promise or predict anything yourself (no "will increase", \
"guarantee", "expected to"). You may describe the forecast of the service and cite its figures.
- Use only numbers that are in the input. Do not invent any and do not calculate new ones.
- "evidence": the numbers of the summary, copied from the input.
- Answer with one JSON object of the given schema and nothing else.
"""

# The line before the input of the overall request; the fake model of the tests reads it.
OVERALL_PREFIX = "OVERALL INPUT:"


def build_overall_prompt(text: str) -> str:
    """The prompt of the overall interpretation; ``text`` is what ``overall_input`` made."""
    return f"{OVERALL_PREFIX}\n{text}"


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _columns(series: ChartSeries) -> tuple[list[str], list[list[object]]]:
    if series.is_forecast:
        rows: list[list[object]] = [[p.label, p.value, p.low, p.high] for p in series.points]
        return ["label", "expected", "low", "high"], rows
    if any(p.numerator is not None for p in series.points):
        rows = [[p.label, p.value, p.numerator, p.denominator] for p in series.points]
        return ["label", "value", "numerator", "denominator"], rows
    return ["label", "value"], [[p.label, p.value] for p in series.points]


def _chart(series: ChartSeries) -> JsonObject:
    columns, rows = _columns(series)
    chart: JsonObject = {
        "id": series.id,
        "title": series.title,
        "unit": series.unit,
        "columns": columns,
        "points": rows,
    }
    if series.is_forecast:
        months, minimum = series.facts
        chart["history_months"] = int(months)
        chart["history_too_short"] = months < minimum
    return chart


def build_user_prompt(name: str, analysis: JsonObject, chart: ChartSeries | None) -> str:
    """The prompt for ``chart`` of the analysis ``name``.

    An analysis without a chart is asked once, about its findings as a whole (``chart`` is None).
    """
    limitations = analysis.get("limitations") or []
    lines = [
        f"Analysis: {name}",
        f"Formula: {analysis.get('formula', '')}",
        f"Limitations: {_compact(limitations)}",
    ]
    if chart is None:
        lines.append(f"Findings: {_compact(analysis.get('findings', {}))}")
        lines.append("This analysis has no chart. Write about its findings as a whole.")
    else:
        lines.append("Write about this chart only:")
    lines.append(f"{CHARTS_PREFIX}{_compact([] if chart is None else [_chart(chart)])}")
    return "\n".join(lines)
