from app.application.documents import JsonObject
from app.application.overall_insight import (
    MAX_OVERALL_INPUT_CHARS,
    figures_of_input,
    overall_input,
)

NAMES = [
    "cancellations",
    "lead_time",
    "room_value",
    "holidays",
    "segments",
    "occupancy",
    "occupancy_on_holidays",
    "correlations",
    "stay_length",
]
LONG_TEXT = "Shares differ between the groups and the weakest group stands out. " * 60


def _findings() -> JsonObject:
    groups = [
        {"figure": {"group": "No Deposit", "numerator": 9450, "denominator": 38199}},
        {"figure": {"group": "Refundable", "numerator": 22, "denominator": 142}},
    ]
    return {"splits": {"by_deposit_type": {"groups": groups}}}


def _analysis(summary: str = LONG_TEXT, *, with_chart: bool = True) -> JsonObject:
    insight: JsonObject = {
        "status": "available",
        "executive_summary": f"- **By deposit type**: {summary}\n- **By segment**: {summary}",
        "improvement_suggestions": [{"suggestion": "RECOMMENDATION " + LONG_TEXT, "evidence": "1"}],
    }
    findings = _findings() if with_chart else {"fields": ["a"]}
    return {"status": "available", "findings": findings, "insight": insight}


def _forecast() -> JsonObject:
    months = [
        {"group": f"2025-{m:02d}", "value": "150.00", "low": "79.29", "high": "220.71"}
        for m in range(1, 13)
    ]
    measure = {"unit": "bookings", "months": months}
    return {"history_months": 30, "measures": {"arrivals": measure, "nights": measure}}


def _full(analyses: dict[str, JsonObject] | None = None) -> tuple[str, dict[str, JsonObject]]:
    analyses = analyses or {name: _analysis() for name in NAMES}
    insights = {name: a["insight"] for name, a in analyses.items()}
    return overall_input(insights, _forecast(), analyses), analyses


def test_the_overall_input_of_a_full_result_is_at_most_the_limit() -> None:
    text, _ = _full()
    assert MAX_OVERALL_INPUT_CHARS == 4000
    assert len(text) <= MAX_OVERALL_INPUT_CHARS


def test_every_available_analysis_and_the_forecast_are_in_the_shortened_input() -> None:
    text, _ = _full()
    for name in NAMES:
        label = name.replace("_", " ").capitalize()
        assert f"Analysis {label}: " in text
        assert f"Largest finding of {label}:" in text
    assert "Forecast arrivals (bookings):" in text
    assert "Forecast nights (bookings):" in text
    assert "2025-12" in text


def test_the_input_holds_the_first_sentence_in_plain_text_and_no_recommendation() -> None:
    text, _ = _full({"cancellations": _analysis("First one. Second one.")})
    assert "Analysis Cancellations: By deposit type: First one." in text
    assert "Second one" not in text
    assert "**" not in text
    assert "RECOMMENDATION" not in text
    assert "- By" not in text


def test_a_short_input_is_not_shortened() -> None:
    summary = "Short sentence about 24.7%."
    text, _ = _full({"cancellations": _analysis(summary)})
    assert f"Analysis Cancellations: By deposit type: {summary}" in text.replace("\n", "")


def test_a_sentence_is_cut_at_a_word_boundary_and_the_figures_of_the_input_stay_allowed() -> None:
    text, _ = _full()
    line = next(x for x in text.splitlines() if x.startswith("Analysis Stay length:"))
    assert line.split()[-1] in {*LONG_TEXT.split(), "groups:"}  # a whole word, not a cut one
    figures = figures_of_input(text)
    assert figures.is_forecast
    assert "150.00" in text


def test_an_analysis_with_no_ai_text_is_named_by_its_largest_finding() -> None:
    analyses = {"cancellations": _analysis(), "holidays": _analysis(with_chart=True)}
    analyses["holidays"]["insight"] = {"status": "unavailable"}
    insights = {"cancellations": analyses["cancellations"]["insight"]}
    text = overall_input(insights, _forecast(), analyses)
    assert "Largest finding of Holidays:" in text
