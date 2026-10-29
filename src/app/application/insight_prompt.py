"""The prompt of one analysis: what the model is told and what figures it is given."""

from __future__ import annotations

import json

from app.application.chart_series import MAX_SERIES, ChartSeries
from app.application.documents import JsonObject

PROMPT_VERSION = "1"
# The line that holds the charts; the fake model of the tests reads it.
CHARTS_PREFIX = "CHARTS: "

SYSTEM_PROMPT = f"""\
You are a careful data analyst for a hotel. You read the figures of one analysis of the \
bookings and write, in English, an executive summary, improvement suggestions and one \
observation for every chart.

Rules:
- Describe observed associations only. Do not claim a cause (no "because", "due to", \
"caused by") and do not forecast or promise (no "will increase", "guarantee").
- Every suggestion has "evidence": the numbers it rests on, copied from the figures, and \
"sample_size": the number of bookings behind them (0 if unknown).
- Write one observation for each chart listed, at most {MAX_SERIES}. Its "series" is the id of \
the chart exactly as listed, its "text" says what you see in that series, and its "evidence" \
names the numbers from that series (as listed, for example 22.3 or 22.3%).
- Use only numbers that are in the figures. Do not invent any.
- Answer with one JSON object of the given schema and nothing else.
"""

RETRY_REMINDER = (
    "Your previous answer was not valid JSON of the required schema. Answer again with only "
    "one JSON object with the keys executive_summary (string), improvement_suggestions (list of "
    "objects with suggestion, evidence, sample_size) and observations (list of objects with "
    "series, text, evidence)."
)


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _chart(series: ChartSeries) -> JsonObject:
    return {
        "id": series.id,
        "title": series.title,
        "unit": series.unit,
        "points": [[p.label, p.value] for p in series.points],
    }


def build_user_prompt(name: str, analysis: JsonObject, charts: list[ChartSeries]) -> str:
    """The figures of the analysis ``name`` and the charts the model may observe."""
    limitations = analysis.get("limitations") or []
    return "\n".join(
        [
            f"Analysis: {name}",
            f"Formula: {analysis.get('formula', '')}",
            f"Limitations: {_compact(limitations)}",
            f"Findings: {_compact(analysis.get('findings', {}))}",
            "Write one observation for each of these charts, with the id as given:",
            f"{CHARTS_PREFIX}{_compact([_chart(c) for c in charts])}",
        ]
    )
