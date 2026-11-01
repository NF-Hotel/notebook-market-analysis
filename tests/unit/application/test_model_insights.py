import json
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.application.analyse_market import analyse_market
from app.application.chart_series import MAX_SERIES, chart_series
from app.application.documents import JsonObject
from app.application.forecast_charts import MEASURE_OF_ANALYSIS
from app.application.insight_guardrail import evidence_is_in_series
from app.application.insight_prompt import PROMPT_VERSION
from app.application.market_result import build_market_result
from app.application.model_insights import ModelInsightProvider
from app.application.ports.model_client import (
    ModelFailedError,
    ModelRequest,
    ModelTimeoutError,
    TimeLimits,
)
from app.domain.booking import Booking
from app.domain.holidays import build_calendar
from app.infrastructure.config import DEFAULT_OLLAMA_NUM_CTX
from tests.unit.ai_fakes import (
    FakeModelClient,
    FakeMonotonicClock,
    Responder,
    answer_json,
    charts_of,
    scripted,
    streaming,
    well_formed_answer,
)
from tests.unit.booking_factory import make_booking

SAMPLE = Path(__file__).parents[3] / "docs" / "test-data" / "market-analysis-result.json"
NOW = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
LIMITS = TimeLimits(stall_seconds=600, total_seconds=14400)
MAX_TOKENS = 32768
GROUPS = {
    "splits": {
        "by_deposit_type": {
            "groups": [
                {"figure": {"group": "No Deposit", "numerator": 9450, "denominator": 38199}},
                {"figure": {"group": "Refundable", "numerator": 22, "denominator": 142}},
            ]
        }
    }
}
SERIES_ID = "splits.by_deposit_type.groups"
SEGMENT_ID = "splits.by_market_segment.groups"
FORECAST_ID = "forecast.arrivals"


def _analysis(findings: JsonObject | None = None, status: str = "available") -> JsonObject:
    return {
        "status": status,
        "reason": None,
        "formula": "share = numerator / denominator",
        "limitations": ["Associations only."],
        "findings": GROUPS if findings is None else findings,
    }


def _provider(client: FakeModelClient) -> ModelInsightProvider:
    return ModelInsightProvider(client, LIMITS, MAX_TOKENS, lambda: NOW)


def _ask(answer: str, analysis: JsonObject | None = None) -> JsonObject:
    provider = _provider(FakeModelClient(scripted(answer, answer)))  # a rejection is asked again
    return provider.insight_for("cancellations", analysis or _analysis())


def _chart_id(request: ModelRequest) -> str:
    (chart,) = charts_of(request)
    return str(chart["id"])


def _two_charts() -> JsonObject:
    segments = {
        "groups": [
            {"figure": {"group": "Online", "numerator": 30, "denominator": 40}},
            {"figure": {"group": "Direct", "numerator": 5, "denominator": 20}},
        ]
    }
    return _analysis({"splits": {**GROUPS["splits"], "by_market_segment": segments}})


def _forecast_part() -> JsonObject:
    months = [
        {"group": "2025-01", "value": "150.00", "low": "79.29", "high": "220.71"},
        {"group": "2025-02", "value": "300.00", "low": "158.58", "high": "441.42"},
    ]
    return {
        "measure": "arrivals",
        "unit": "bookings",
        "history_months": 30,
        "minimum_history_months": 24,
        "history_too_short": False,
        "months": months,
    }


def _forecast_analysis() -> JsonObject:
    """An analysis with no chart of its own and the forecast of the service."""
    return {**_analysis({"fields": ["a"]}), "forecast": _forecast_part()}


def _rec(suggestion: str = "Check it.", evidence: str = "15.5") -> dict[str, object]:
    return {"suggestion": suggestion, "evidence": evidence, "sample_size": 3}


def test_info_names_the_provider_the_model_and_the_prompt_version() -> None:
    info = _provider(FakeModelClient(scripted())).info()
    assert info == {"provider": "fake", "model": "fake-1", "prompt_version": "6"}
    assert PROMPT_VERSION == "6"


def test_an_available_insight_carries_the_label_provider_model_and_time() -> None:
    insight = _ask(answer_json())
    assert insight["status"] == "available"
    assert insight["reason"] is None
    assert insight["label"] == "AI-generated"
    assert (insight["provider"], insight["model"]) == ("fake", "fake-1")
    assert insight["generated_at"] == NOW.isoformat()
    assert (
        insight["executive_summary"] == "- **By deposit type**: Shares differ between the groups."
    )
    assert insight["improvement_suggestions"] == [
        {
            "suggestion": "Look at the weakest group.",
            "evidence": "It is 15.5 here.",
            "sample_size": 80,
            "series": SERIES_ID,
        }
    ]
    assert insight["observations"] == [
        {"series": SERIES_ID, "text": "Shares differ between the groups.", "evidence": "24.7"}
    ]


def test_the_request_carries_the_maximum_output_tokens_the_schema_and_the_limits() -> None:
    client = FakeModelClient(well_formed_answer)
    _provider(client).insight_for("cancellations", _analysis())
    (request,) = client.requests
    assert request.max_output_tokens == 32768
    assert request.limits == LIMITS
    assert set(request.schema["required"]) == {"summary", "evidence", "recommendations"}


def test_the_prompt_holds_the_chart_its_counts_and_the_rules() -> None:
    client = FakeModelClient(well_formed_answer)
    _provider(client).insight_for("cancellations", _analysis())
    (request,) = client.requests
    assert "Analysis: cancellations" in request.user
    assert "share = numerator / denominator" in request.user
    assert "Associations only." in request.user
    assert "9450" in request.user  # the counts behind a share are in the chart
    assert [c["id"] for c in charts_of(request)] == [SERIES_ID]
    assert "associations only" in request.system
    assert "Markdown" in request.system
    assert "bold" in request.system
    assert "recommendations" in request.system


def test_the_service_makes_one_request_for_each_chart() -> None:
    client = FakeModelClient(well_formed_answer)
    insight = _provider(client).insight_for("cancellations", _two_charts())
    assert [_chart_id(r) for r in client.requests] == [SERIES_ID, SEGMENT_ID]
    assert [o["series"] for o in insight["observations"]] == [SERIES_ID, SEGMENT_ID]
    # The summaries of the charts are joined and each recommendation names its chart.
    assert insight["executive_summary"].count("is the first group of the chart") == 2
    assert [s["series"] for s in insight["improvement_suggestions"]] == [SERIES_ID, SEGMENT_ID]


def test_a_chart_the_guardrail_rejects_loses_only_its_own_text() -> None:
    def respond(request: ModelRequest) -> str:
        if _chart_id(request) == SERIES_ID:
            return answer_json(summary="Cancellations rise because of the price.")
        return well_formed_answer(request)

    client = FakeModelClient(respond)
    insight = _provider(client).insight_for("cancellations", _two_charts())
    assert len(client.requests) == 3  # the rejected chart is asked once more
    assert insight["status"] == "available"
    assert [o["series"] for o in insight["observations"]] == [SEGMENT_ID]
    assert "because" not in insight["executive_summary"]
    assert {s["series"] for s in insight["improvement_suggestions"]} == {SEGMENT_ID}


def test_an_analysis_whose_charts_are_all_rejected_is_rejected() -> None:
    insight = _ask(answer_json(summary="Sales will increase."))
    assert (insight["status"], insight["reason"]) == ("unavailable", "GUARDRAIL_REJECTED")
    assert "executive_summary" not in insight


@pytest.mark.parametrize(
    "changes",
    [
        {"summary": "Cancellations rise due to the price."},
        {"summary": "This guarantees growth."},
        {"evidence": "24.7 and 99.9"},
        {"evidence": "No numbers."},
        {"summary": "No Deposit is 99.9 here."},
        {"recommendations": [_rec("It leads to 15.5.")]},
        {"recommendations": [_rec("Sales will rise.")]},
    ],
    ids=[
        "cause",
        "promise",
        "unknown-figure",
        "no-number",
        "unknown-figure-in-text",
        "recommendation-cause",
        "recommendation-promise",
    ],
)
def test_a_chart_text_with_a_cause_a_promise_or_a_figure_not_in_the_series_is_rejected(
    changes: dict[str, object],
) -> None:
    insight = _ask(answer_json(**changes))
    assert (insight["status"], insight["reason"]) == ("unavailable", "GUARDRAIL_REJECTED")


def test_a_blank_summary_is_rejected() -> None:
    assert _ask(answer_json(summary="  "))["reason"] == "GUARDRAIL_REJECTED"


def test_a_recommendation_whose_evidence_does_not_check_out_is_dropped_and_the_summary_stays() -> (
    None
):
    no_number = _rec("Do more.", "Looks good.")
    wrong_number = _rec("Do less.", "It is 77.7.")
    insight = _ask(answer_json(recommendations=[no_number, wrong_number, _rec()]))
    assert insight["status"] == "available"
    assert [s["suggestion"] for s in insight["improvement_suggestions"]] == ["Check it."]


def test_at_most_three_recommendations_are_kept_for_a_chart() -> None:
    insight = _ask(answer_json(recommendations=[_rec()] * 5))
    assert len(insight["improvement_suggestions"]) == 3


def test_the_counts_and_the_labels_of_a_chart_may_be_cited() -> None:
    summary = "No Deposit has 9450 of 38199 bookings, 24.7 percent."
    insight = _ask(answer_json(summary=summary, evidence="9450 and 38199"))
    assert insight["status"] == "available"


def test_the_forecast_of_the_service_may_be_described_with_its_figures() -> None:
    answer = answer_json(
        summary="The forecast for 2025-01 is 150.00 arrivals, between 79.29 and 220.71, "
        "from 30 months of history.",
        evidence="150.00, 79.29, 220.71, 30",
        recommendations=[_rec("Plan staff for the projected 300.00 of 2025-02.", "300.00")],
    )
    client = FakeModelClient(scripted(answer))
    insight = _provider(client).insight_for("seasonality", _forecast_analysis())
    assert insight["status"] == "available"
    assert [_chart_id(r) for r in client.requests] == [FORECAST_ID]
    assert insight["observations"][0]["series"] == FORECAST_ID
    assert len(insight["improvement_suggestions"]) == 1


@pytest.mark.parametrize(
    "summary",
    [
        "The forecast says 150.00 and the arrivals will increase.",  # a promise
        "The forecast of 150.00 arrivals is due to the season.",  # a cause
        "The forecast is 999.00 arrivals.",  # a figure that is not in the input
        "We predict 150.00 arrivals.",  # a forecast of the model itself
    ],
    ids=["promise", "cause", "unknown-figure", "own-prediction"],
)
def test_the_forecast_chart_still_rejects_a_promise_a_cause_and_an_unknown_figure(
    summary: str,
) -> None:
    rejected = answer_json(summary=summary, evidence="150.00")
    client = FakeModelClient(scripted(rejected, rejected))
    insight = _provider(client).insight_for("seasonality", _forecast_analysis())
    assert (insight["status"], insight["reason"]) == ("unavailable", "GUARDRAIL_REJECTED")


def test_the_word_forecast_is_rejected_on_a_chart_that_is_not_the_forecast_of_the_service() -> None:
    insight = _ask(answer_json(summary="The forecast of 24.7 is high."))
    assert insight["reason"] == "GUARDRAIL_REJECTED"


def test_the_forecast_is_a_chart_beside_the_charts_of_the_findings() -> None:
    analysis = {**_analysis(), "forecast": _forecast_part()}
    client = FakeModelClient(well_formed_answer)
    insight = _provider(client).insight_for("seasonality", analysis)
    assert [_chart_id(r) for r in client.requests] == [SERIES_ID, FORECAST_ID]
    assert [o["series"] for o in insight["observations"]] == [SERIES_ID, FORECAST_ID]


def test_the_prompt_of_the_forecast_chart_says_how_long_the_history_is() -> None:
    client = FakeModelClient(well_formed_answer)
    _provider(client).insight_for("seasonality", _forecast_analysis())
    (request,) = client.requests
    (chart,) = charts_of(request)
    assert chart["columns"] == ["label", "expected", "low", "high"]
    assert (chart["history_months"], chart["history_too_short"]) == (30, False)
    assert 'starts with "forecast."' in request.system


def test_an_analysis_without_charts_is_asked_once_about_its_findings() -> None:
    client = FakeModelClient(well_formed_answer)
    insight = _provider(client).insight_for("correlations", _analysis({"fields": ["a"]}))
    (request,) = client.requests
    assert charts_of(request) == []
    assert '"fields":["a"]' in request.user
    assert insight["status"] == "available"
    assert insight["observations"] == []
    assert insight["executive_summary"]


def test_a_bad_structure_is_asked_once_more_with_a_reminder() -> None:
    client = FakeModelClient(scripted("not json", answer_json()))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert insight["status"] == "available"
    first, second = client.requests
    assert "previous answer was not valid JSON" not in first.user
    assert "previous answer was not valid JSON" in second.user
    assert [r.max_output_tokens for r in client.requests] == [32768, 32768]


def test_a_second_bad_structure_gives_bad_structure_after_two_requests() -> None:
    client = FakeModelClient(scripted("not json", '{"summary": 3}'))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert (insight["status"], insight["reason"]) == ("unavailable", "BAD_STRUCTURE")
    assert len(client.requests) == 2


def test_a_chart_with_a_bad_structure_does_not_remove_the_others() -> None:
    second = answer_json(evidence="75.0", recommendations=[_rec(evidence="25.0")])
    client = FakeModelClient(scripted("a", "b", second))
    insight = _provider(client).insight_for("cancellations", _two_charts())
    assert len(client.requests) == 3
    assert insight["status"] == "available"
    assert [o["series"] for o in insight["observations"]] == [SEGMENT_ID]


@pytest.mark.parametrize(
    "outcome",
    [ModelFailedError("unreachable"), "", "   ", RuntimeError("boom")],
    ids=["failed", "empty", "blank", "unexpected"],
)
def test_a_model_failure_or_an_empty_answer_gives_model_error_without_retry(
    outcome: str | Exception,
) -> None:
    client = FakeModelClient(scripted(outcome))
    insight = _provider(client).insight_for("cancellations", _two_charts())
    assert (insight["status"], insight["reason"]) == ("unavailable", "MODEL_ERROR")
    assert len(client.requests) == 1  # the other chart is not asked after a failure


def test_a_timeout_gives_timeout_without_retry_and_stops_the_analysis() -> None:
    client = FakeModelClient(scripted(ModelTimeoutError("slow")))
    insight = _provider(client).insight_for("cancellations", _two_charts())
    assert (insight["status"], insight["reason"]) == ("unavailable", "TIMEOUT")
    assert len(client.requests) == 1


def test_a_timeout_after_some_charts_keeps_the_text_of_those_charts() -> None:
    client = FakeModelClient(scripted(answer_json(), ModelTimeoutError("slow")))
    insight = _provider(client).insight_for("cancellations", _two_charts())
    assert insight["status"] == "available"
    assert len(insight["observations"]) == 1


def test_an_analysis_without_data_is_not_asked() -> None:
    client = FakeModelClient(scripted())
    insight = _provider(client).insight_for("room_value", _analysis(status="unavailable"))
    assert insight["reason"] == "ANALYSIS_UNAVAILABLE"
    assert client.requests == []


def _lead_time_stalls(clock: FakeMonotonicClock) -> Responder:
    stalling = streaming(clock, [(LIMITS.stall_seconds, "{")])
    good = streaming(clock, [(1, answer_json())])

    def respond(request: ModelRequest) -> str:
        return stalling(request) if "Analysis: lead_time" in request.user else good(request)

    return respond


def test_a_model_without_a_token_for_the_stall_timeout_times_out_for_that_analysis_only() -> None:
    provider = _provider(FakeModelClient(_lead_time_stalls(FakeMonotonicClock())))
    first = provider.insight_for("lead_time", _analysis())
    second = provider.insight_for("holidays", _analysis())
    assert (first["status"], first["reason"]) == ("unavailable", "TIMEOUT")
    assert second["status"] == "available"


def test_a_model_that_keeps_sending_tokens_is_not_stopped_before_the_total_limit() -> None:
    clock = FakeMonotonicClock()
    pieces = [(100.0, " ")] * 142 + [(100.0, answer_json())]  # the last token at 14300 s
    provider = _provider(FakeModelClient(streaming(clock, pieces)))
    assert provider.insight_for("lead_time", _analysis())["status"] == "available"


def test_a_model_that_keeps_sending_tokens_is_stopped_at_the_total_limit() -> None:
    clock = FakeMonotonicClock()
    pieces = [(100.0, " ")] * 143 + [(100.0, answer_json())]  # the last token at 14400 s
    provider = _provider(FakeModelClient(streaming(clock, pieces)))
    insight = provider.insight_for("lead_time", _analysis())
    assert (insight["status"], insight["reason"]) == ("unavailable", "TIMEOUT")


def test_the_sample_result_gets_a_summary_and_recommendations_for_every_chart() -> None:
    analyses = json.loads(SAMPLE.read_text(encoding="utf-8"))["analyses"]
    client = FakeModelClient(well_formed_answer)
    provider = _provider(client)
    for name, analysis in analyses.items():
        before = len(client.requests)
        insight = provider.insight_for(name, analysis)
        charts = {c.id: c for c in chart_series(analysis["findings"])}
        assert insight["status"] == "available", name
        assert insight["executive_summary"]
        assert insight["improvement_suggestions"]
        assert [o["series"] for o in insight["observations"]] == list(charts)
        assert len(client.requests) - before == max(1, len(charts))
        assert len(charts) <= MAX_SERIES
        for observation in insight["observations"]:
            assert evidence_is_in_series(observation["evidence"], charts[observation["series"]])


def _bookings(count: int = 200) -> list[Booking]:
    rng = random.Random(5)  # noqa: S311 - seeded test data
    result = []
    for number in range(count):
        arrival = date(2023, 1, 1) + timedelta(days=rng.randrange(500))
        lead = rng.randrange(150)
        result.append(
            make_booking(
                booking_id=number,
                is_canceled=rng.random() < 0.3,
                arrival_date=arrival,
                booking_date=arrival - timedelta(days=lead),
                lead_time=lead,
                stays_in_week_nights=rng.randrange(1, 6),
                country=rng.choice(["PRT", "GBR", "FRA"]),
                market_segment=rng.choice(["Online", "Direct"]),
                customer_type=rng.choice(["Transient", "Contract"]),
                deposit_type=rng.choice(["No Deposit", "Refundable"]),
                price_per_night=Decimal(rng.randrange(5000, 20000)) / 100,
            )
        )
    return result


def _build(provider: ModelInsightProvider | None) -> JsonObject:
    bookings = _bookings()
    calendar = build_calendar(2022, 2026)
    analysis = analyse_market(bookings, 20, calendar)
    return build_market_result(analysis, bookings, calendar, "id", NOW, provider)


def test_every_analysis_of_a_run_gets_its_insight_and_every_chart_its_text() -> None:
    client = FakeModelClient(well_formed_answer)
    result = _build(_provider(client))
    analyses = result["analyses"]
    assert len(analyses) == 9
    assert result["insights"] == {
        "requested": True,
        "provider": "fake",
        "model": "fake-1",
        "prompt_version": "6",
        "overall": result["insights"]["overall"],
    }
    assert result["insights"]["overall"]["source"] == "ai"
    requests = 1  # the overall interpretation
    for name, analysis in analyses.items():
        insight = analysis["insight"]
        assert insight["status"] == "available", name
        expected = [c.id for c in chart_series(analysis["findings"])]
        if name in MEASURE_OF_ANALYSIS:
            expected.append(f"forecast.{MEASURE_OF_ANALYSIS[name]}")
        assert [o["series"] for o in insight["observations"]] == expected
        assert "forecast" not in analysis  # the part of the forecast is not stored in the analysis
        requests += len(expected) or 1
    assert len(client.requests) == requests


def test_a_rejected_analysis_does_not_touch_the_others_or_the_numbers() -> None:
    def respond(request: ModelRequest) -> str:
        if "Analysis: seasonality" in request.user:
            return answer_json(summary="This guarantees growth.")
        return well_formed_answer(request)

    with_ai = _build(_provider(FakeModelClient(respond)))
    without_ai = _build(None)
    statuses = {n: a["insight"]["status"] for n, a in with_ai["analyses"].items()}
    assert [n for n, s in statuses.items() if s != "available"] == ["seasonality"]
    assert with_ai["analyses"]["seasonality"]["insight"]["reason"] == "GUARDRAIL_REJECTED"
    assert with_ai["notices"][-1]["code"] == "INSIGHTS_UNAVAILABLE"
    for name, analysis in with_ai["analyses"].items():
        assert analysis["findings"] == without_ai["analyses"][name]["findings"]
    assert with_ai["forecast"] == without_ai["forecast"]


def test_a_rejected_chart_of_a_run_leaves_the_other_charts_of_its_analysis() -> None:
    rejected = "splits.by_deposit_type.groups"

    def respond(request: ModelRequest) -> str:
        if _chart_id_or_none(request) == rejected:
            return answer_json(summary="Because of the deposit.")
        return well_formed_answer(request)

    insight = _build(_provider(FakeModelClient(respond)))["analyses"]["cancellations"]["insight"]
    assert insight["status"] == "available"
    series = [o["series"] for o in insight["observations"]]
    assert rejected not in series
    assert len(series) >= 1


def _chart_id_or_none(request: ModelRequest) -> str | None:
    charts = charts_of(request)
    return str(charts[0]["id"]) if charts else None


def test_with_insights_off_there_is_no_insight_and_no_call() -> None:
    result = _build(None)
    assert all("insight" not in a for a in result["analyses"].values())
    assert result["insights"]["requested"] is False
    assert result["insights"]["overall"]["source"] == "figures"


def test_the_executive_summary_is_a_markdown_list_with_a_bold_chart_name_for_each_chart() -> None:
    insight = _provider(FakeModelClient(well_formed_answer)).insight_for(
        "cancellations", _two_charts()
    )
    lines = insight["executive_summary"].split("\n")
    assert [line.split("**")[1] for line in lines] == ["By deposit type", "By market segment"]
    assert all(line.startswith("- **") for line in lines)


def test_a_summary_with_several_lines_stays_inside_its_list_item() -> None:
    insight = _ask(answer_json(summary="Lead.\n\nSecond paragraph, **24.7%**."))
    assert insight["executive_summary"] == (
        "- **By deposit type**: Lead. Second paragraph, **24.7%**."
    )


def test_a_list_inside_a_summary_becomes_plain_sentences_and_the_bold_figures_pass_the_checks() -> (
    None
):
    summary = "No Deposit is the largest. - **No Deposit**: **24.7%** - **Refundable**: 15.5%"
    insight = _ask(answer_json(summary=summary))
    assert insight["status"] == "available"
    assert insight["observations"][0]["text"] == (
        "No Deposit is the largest. **No Deposit**: **24.7%**. **Refundable**: 15.5%."
    )
    assert insight["executive_summary"].count("\n") == 0


def test_a_first_rejection_is_asked_once_more_with_the_rules_and_a_good_answer_is_kept() -> None:
    client = FakeModelClient(scripted(answer_json(summary="Rises because of it."), answer_json()))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert insight["status"] == "available"
    first, second = client.requests
    assert "rejected by the checks" not in first.user
    assert second.user.startswith(first.user)
    assert "rejected by the checks" in second.user
    assert "no cause, no promise and no prediction" in second.user


def test_two_rejections_leave_the_chart_without_text_after_two_requests() -> None:
    bad = answer_json(summary="Rises because of it.")
    client = FakeModelClient(scripted(bad, bad))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert (insight["status"], insight["reason"]) == ("unavailable", "GUARDRAIL_REJECTED")
    assert len(client.requests) == 2


def test_raw_html_is_removed_from_the_answer_and_the_list_is_flattened() -> None:
    summary = "<script>alert(1)</script>Lead.\n- **No Deposit**: <b>24.7</b>%<style>p{}</style>"
    rec = _rec("<img src=x onerror=1>Check it.", "15.5")
    insight = _ask(answer_json(summary=summary, recommendations=[rec]))
    assert insight["status"] == "available"
    assert insight["observations"][0]["text"] == "Lead. **No Deposit**: 24.7%."
    assert insight["improvement_suggestions"][0]["suggestion"] == "Check it."
    assert "<" not in insight["executive_summary"]
    assert "alert" not in insight["executive_summary"]


def _run_texts() -> dict[str, JsonObject]:
    analysis = _analysis()
    insight = _provider(FakeModelClient(well_formed_answer)).insight_for("cancellations", analysis)
    return {"cancellations": {**analysis, "insight": insight}}


def _forecast_input() -> JsonObject:
    return {
        "history_months": 30,
        "measures": {"arrivals": {"unit": "bookings", "months": _forecast_part()["months"]}},
    }


def _overall_answer(**changes: object) -> str:
    return answer_json(
        summary="## Key points\n- **No Deposit**: 24.7%, forecast 150.00 for 2025-01.",
        evidence="24.7, 150.00",
        recommendations=[_rec("Look at 24.7.", "24.7"), _rec("Check 300.00.", "300.00")],
        **changes,
    )


def test_the_overall_interpretation_is_one_extra_request_about_the_texts_not_the_bookings() -> None:
    texts = _run_texts()
    client = FakeModelClient(scripted(_overall_answer()))
    overall = _provider(client).overall_for(texts, _forecast_input())
    (request,) = client.requests
    assert request.system.count("Markdown") >= 1
    assert "OVERALL INPUT:" in request.user
    assert (
        "Analysis Cancellations: By deposit type: No Deposit is the first group of the chart."
        in (request.user)
    )
    assert "300.00" in request.user  # the forecast of the service is input
    assert overall is not None
    assert (overall["status"], overall["source"], overall["label"]) == (
        "available",
        "ai",
        "AI-generated",
    )
    assert overall["generated_at"] == NOW.isoformat()
    assert overall["text"].startswith("## Key points")
    assert len(overall["recommendations"]) == 2
    assert all("series" not in r for r in overall["recommendations"])


@pytest.mark.parametrize(
    "changes",
    [
        {"summary": "Sales will increase."},
        {"summary": "The deposit is the cause: 24.7 because of it."},
        {"summary": "No Deposit is 31.4 here."},  # a number that is not in the input
        {"evidence": "no number"},
    ],
    ids=["promise", "cause", "unknown-figure", "no-evidence"],
)
def test_a_rejected_overall_text_gives_none_and_leaves_the_analyses_alone(
    changes: dict[str, object],
) -> None:
    texts = _run_texts()
    before = json.dumps(texts, sort_keys=True)
    bad = json.dumps({**json.loads(_overall_answer()), **changes})
    client = FakeModelClient(scripted(bad, bad))
    assert _provider(client).overall_for(texts, _forecast_input()) is None
    assert json.dumps(texts, sort_keys=True) == before


def test_an_overall_text_that_describes_the_forecast_of_the_service_is_kept() -> None:
    answer = answer_json(
        summary="The forecast shows 150.00 for 2025-01, projected from the history.",
        evidence="150.00",
        recommendations=[_rec("Look at 24.7.", "24.7")],
    )
    client = FakeModelClient(scripted(answer))
    assert _provider(client).overall_for(_run_texts(), _forecast_input()) is not None
    assert len(client.requests) == 1


def test_a_forecast_figure_written_wrongly_in_the_overall_text_is_rejected() -> None:
    answer = answer_json(
        summary="The forecast shows 1,278 for 2025-01.",  # not a figure of the input
        evidence="150.00",
        recommendations=[_rec("Look at 24.7.", "24.7")],
    )
    client = FakeModelClient(scripted(answer, answer))
    assert _provider(client).overall_for(_run_texts(), _forecast_input()) is None


def test_a_first_overall_rejection_is_asked_once_more_and_a_good_answer_is_kept() -> None:
    bad = answer_json(summary="Sales will increase.")
    client = FakeModelClient(scripted(bad, _overall_answer()))
    overall = _provider(client).overall_for(_run_texts(), _forecast_input())
    assert overall is not None
    first, second = client.requests
    assert "OVERALL INPUT:" in second.user
    assert second.user.startswith(first.user)
    assert "rejected by the checks" in second.user
    assert "rejected by the checks" not in first.user


def test_two_overall_rejections_give_none_after_exactly_two_requests() -> None:
    bad = answer_json(summary="Sales will increase.")
    client = FakeModelClient(scripted(bad, bad))
    assert _provider(client).overall_for(_run_texts(), _forecast_input()) is None
    assert len(client.requests) == 2


@pytest.mark.parametrize("outcome", [ModelFailedError("x"), ModelTimeoutError("x")])
def test_an_overall_timeout_or_model_error_is_not_asked_again(outcome: Exception) -> None:
    client = FakeModelClient(scripted(outcome, _overall_answer()))
    assert _provider(client).overall_for(_run_texts(), _forecast_input()) is None
    assert len(client.requests) == 1


def test_the_overall_prompt_tells_the_model_to_copy_the_forecast_figures() -> None:
    client = FakeModelClient(scripted(_overall_answer()))
    _provider(client).overall_for(_run_texts(), _forecast_input())
    assert "exactly as written in the input" in client.requests[0].system


def test_the_overall_text_may_cite_the_forecast_and_dates_after_a_month_name() -> None:
    answer = answer_json(
        summary="The forecast of the service is 150.00 from January 2025.",
        evidence="150.00",
        recommendations=[_rec("Look at 24.7.", "24.7")],
    )
    overall = _provider(FakeModelClient(scripted(answer))).overall_for(
        _run_texts(), _forecast_input()
    )
    assert overall is not None


def test_the_overall_request_names_the_largest_finding_of_every_analysis_with_findings() -> None:
    texts = _run_texts()
    texts["lead_time"] = {**_two_charts(), "insight": texts["cancellations"]["insight"]}
    texts["room_value"] = _analysis({"fields": ["a"]})  # available, but no chart
    texts["holidays"] = {**_analysis(), "insight": {"status": "unavailable"}}  # no AI text
    client = FakeModelClient(scripted(_overall_answer()))
    _provider(client).overall_for(texts, _forecast_input())
    (request,) = client.requests
    assert "Largest finding of Cancellations: By deposit type: No Deposit is the largest" in (
        request.user
    )
    assert "Largest finding of Lead time:" in request.user
    assert "Largest finding of Holidays:" in request.user  # an analysis with no AI text too
    assert "Largest finding of Room value" not in request.user  # no chart, no figure


def test_a_largest_finding_of_the_input_is_an_allowed_number_of_the_overall_text() -> None:
    texts = _run_texts()
    segments = _two_charts()["findings"]["splits"]["by_market_segment"]
    holidays = _analysis({"splits": {"by_market_segment": segments}})
    texts["holidays"] = {**holidays, "insight": {"status": "unavailable"}}
    answer = answer_json(
        summary="Online is the largest at 75%.", evidence="75", recommendations=[_rec()]
    )
    overall = _provider(FakeModelClient(scripted(answer))).overall_for(texts, _forecast_input())
    assert overall is not None


def test_the_overall_interpretation_is_not_asked_when_no_analysis_has_text() -> None:
    client = FakeModelClient(scripted())
    unavailable = {"room_value": {**_analysis(), "insight": {"status": "unavailable"}}}
    assert _provider(client).overall_for(unavailable, _forecast_input()) is None
    assert client.requests == []


@pytest.mark.parametrize("outcome", [ModelFailedError("x"), ModelTimeoutError("x"), "not json"])
def test_a_failed_overall_request_gives_none(outcome: str | Exception) -> None:
    client = FakeModelClient(scripted(outcome, outcome))
    assert _provider(client).overall_for(_run_texts(), _forecast_input()) is None


def test_a_run_with_a_rejected_overall_text_has_the_figures_fallback_and_the_same_analyses() -> (
    None
):
    def respond(request: ModelRequest) -> str:
        if "OVERALL INPUT:" in request.user:
            return answer_json(summary="This guarantees growth.")
        return well_formed_answer(request)

    rejected = _build(_provider(FakeModelClient(respond)))
    accepted = _build(_provider(FakeModelClient(well_formed_answer)))
    assert rejected["insights"]["overall"]["source"] == "figures"
    assert rejected["insights"]["overall"]["label"] == "Calculated from the figures"
    for name, analysis in rejected["analyses"].items():
        assert analysis["insight"] == accepted["analyses"][name]["insight"]
    assert rejected["notices"] == accepted["notices"]


def test_with_ai_off_the_overall_is_the_fallback_from_the_largest_finding_of_each_analysis() -> (
    None
):
    overall = _build(None)["insights"]["overall"]
    assert (overall["status"], overall["source"]) == ("available", "figures")
    assert overall["text"].startswith("**Key figures**\n\n- **")
    assert "is the largest at" in overall["text"]
    assert "recommendations" not in overall


def test_the_default_context_window_holds_the_longest_prompt_of_a_full_run() -> None:
    def respond(request: ModelRequest) -> str:
        answer = json.loads(well_formed_answer(request))
        answer["summary"] += " The groups differ in size and in share." * 80
        return json.dumps(answer)

    client = FakeModelClient(respond)
    _build(_provider(client))
    longest = max(len(r.system) + len(r.user) for r in client.requests)
    assert any("OVERALL INPUT:" in r.user for r in client.requests)
    assert longest / 3 < DEFAULT_OLLAMA_NUM_CTX  # a token is about three characters
