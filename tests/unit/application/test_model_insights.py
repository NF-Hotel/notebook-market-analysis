import json
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.application.analyse_market import analyse_market
from app.application.chart_series import MAX_SERIES, chart_series
from app.application.documents import JsonObject
from app.application.insight_guardrail import evidence_is_in_series
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
NO_CHARTS_REQUEST = ModelRequest("", "Analysis: x", {}, 1, LIMITS)


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


def _observation(**changes: str) -> dict[str, str]:
    observation = {
        "series": SERIES_ID,
        "text": "No Deposit is higher.",
        "evidence": "24.7 and 15.5",
    }
    observation.update(changes)
    return observation


def _ask(answer: str, analysis: JsonObject | None = None) -> JsonObject:
    provider = _provider(FakeModelClient(scripted(answer)))
    return provider.insight_for("cancellations", analysis or _analysis())


def test_info_names_the_provider_the_model_and_the_prompt_version() -> None:
    info = _provider(FakeModelClient(scripted())).info()
    assert info == {"provider": "fake", "model": "fake-1", "prompt_version": "1"}


def test_an_available_insight_carries_the_label_provider_model_and_time() -> None:
    insight = _ask(answer_json(observations=[_observation()]))
    assert insight["status"] == "available"
    assert insight["reason"] is None
    assert insight["label"] == "AI-generated"
    assert (insight["provider"], insight["model"]) == ("fake", "fake-1")
    assert insight["generated_at"] == NOW.isoformat()
    assert insight["executive_summary"] == "Shares differ between the groups."
    assert insight["improvement_suggestions"] == [
        {
            "suggestion": "Look at the weakest group.",
            "evidence": "It is 12.5 here.",
            "sample_size": 80,
        }
    ]
    assert insight["observations"] == [_observation()]


def test_the_request_carries_the_maximum_output_tokens_the_schema_and_the_limits() -> None:
    client = FakeModelClient(well_formed_answer)
    _provider(client).insight_for("cancellations", _analysis())
    (request,) = client.requests
    assert request.max_output_tokens == 32768
    assert request.limits == LIMITS
    assert set(request.schema["required"]) == {
        "executive_summary",
        "improvement_suggestions",
        "observations",
    }


def test_the_prompt_holds_the_figures_the_charts_and_the_rules() -> None:
    client = FakeModelClient(well_formed_answer)
    _provider(client).insight_for("cancellations", _analysis())
    (request,) = client.requests
    assert "Analysis: cancellations" in request.user
    assert "share = numerator / denominator" in request.user
    assert "Associations only." in request.user
    assert '"numerator":9450' in request.user
    assert [c["id"] for c in charts_of(request)] == [SERIES_ID]
    assert "associations only" in request.system
    assert "forecast" in request.system


def test_a_causal_summary_is_rejected_by_the_guardrail() -> None:
    insight = _ask(answer_json(executive_summary="Cancellations rise because of the price."))
    assert insight["status"] == "unavailable"
    assert insight["reason"] == "GUARDRAIL_REJECTED"
    assert "executive_summary" not in insight


def test_a_forecast_in_a_suggestion_is_rejected_by_the_guardrail() -> None:
    suggestion = {"suggestion": "Sales will increase.", "evidence": "It is 3.", "sample_size": 3}
    insight = _ask(answer_json(improvement_suggestions=[suggestion]))
    assert insight["reason"] == "GUARDRAIL_REJECTED"


def test_a_blank_summary_is_rejected() -> None:
    assert _ask(answer_json(executive_summary="  "))["reason"] == "GUARDRAIL_REJECTED"


def test_a_suggestion_whose_evidence_names_no_number_is_dropped() -> None:
    suggestion = {"suggestion": "Do more.", "evidence": "Looks good.", "sample_size": 3}
    insight = _ask(answer_json(improvement_suggestions=[suggestion]))
    assert insight["status"] == "available"
    assert insight["improvement_suggestions"] == []


@pytest.mark.parametrize(
    "dropped",
    [
        _observation(evidence="24.7 and 99.9"),
        _observation(evidence="No numbers."),
        _observation(series="splits.other.groups"),
        _observation(text="This will increase."),
    ],
)
def test_an_observation_that_does_not_check_out_is_dropped_and_the_rest_stays(
    dropped: dict[str, str],
) -> None:
    insight = _ask(answer_json(observations=[dropped, _observation(evidence="15.5")]))
    assert insight["status"] == "available"
    assert insight["observations"] == [_observation(evidence="15.5")]


def test_only_one_observation_is_kept_for_a_chart() -> None:
    insight = _ask(answer_json(observations=[_observation(), _observation(evidence="15.5")]))
    assert insight["observations"] == [_observation()]


def test_an_analysis_without_charts_has_no_observations() -> None:
    insight = _ask(well_formed_answer(NO_CHARTS_REQUEST), _analysis({"fields": ["a"]}))
    assert insight["status"] == "available"
    assert insight["observations"] == []


def test_a_bad_structure_is_asked_once_more_with_a_reminder() -> None:
    client = FakeModelClient(scripted("not json", answer_json()))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert insight["status"] == "available"
    first, second = client.requests
    assert "previous answer was not valid JSON" not in first.user
    assert "previous answer was not valid JSON" in second.user
    assert [r.max_output_tokens for r in client.requests] == [32768, 32768]


def test_a_second_bad_structure_gives_bad_structure_after_two_requests() -> None:
    client = FakeModelClient(scripted("not json", '{"executive_summary": 3}'))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert (insight["status"], insight["reason"]) == ("unavailable", "BAD_STRUCTURE")
    assert len(client.requests) == 2


@pytest.mark.parametrize(
    "outcome",
    [ModelFailedError("unreachable"), "", "   ", RuntimeError("boom")],
    ids=["failed", "empty", "blank", "unexpected"],
)
def test_a_model_failure_or_an_empty_answer_gives_model_error_without_retry(
    outcome: str | Exception,
) -> None:
    client = FakeModelClient(scripted(outcome))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert (insight["status"], insight["reason"]) == ("unavailable", "MODEL_ERROR")
    assert len(client.requests) == 1


def test_a_timeout_gives_timeout_without_retry() -> None:
    client = FakeModelClient(scripted(ModelTimeoutError("slow")))
    insight = _provider(client).insight_for("cancellations", _analysis())
    assert (insight["status"], insight["reason"]) == ("unavailable", "TIMEOUT")
    assert len(client.requests) == 1


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


def test_the_sample_result_gets_an_insight_for_every_analysis_with_observations_per_chart() -> None:
    analyses = json.loads(SAMPLE.read_text(encoding="utf-8"))["analyses"]
    provider = _provider(FakeModelClient(well_formed_answer))
    for name, analysis in analyses.items():
        insight = provider.insight_for(name, analysis)
        charts = {c.id: c for c in chart_series(analysis["findings"])}
        assert insight["status"] == "available", name
        assert insight["executive_summary"]
        assert insight["improvement_suggestions"]
        assert [o["series"] for o in insight["observations"]] == list(charts)
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


def test_every_one_of_the_nine_analyses_of_a_run_gets_its_insight() -> None:
    client = FakeModelClient(well_formed_answer)
    result = _build(_provider(client))
    analyses = result["analyses"]
    assert len(analyses) == 9
    assert len(client.requests) == 9
    assert result["insights"] == {
        "requested": True,
        "provider": "fake",
        "model": "fake-1",
        "prompt_version": "1",
    }
    for analysis in analyses.values():
        insight = analysis["insight"]
        assert insight["status"] == "available"
        charts = chart_series(analysis["findings"])
        assert len(insight["observations"]) == len(charts) <= MAX_SERIES


def test_a_rejected_analysis_does_not_touch_the_others_or_the_numbers() -> None:
    def respond(request: ModelRequest) -> str:
        if "Analysis: seasonality" in request.user:
            return answer_json(executive_summary="This guarantees growth.")
        return well_formed_answer(request)

    with_ai = _build(_provider(FakeModelClient(respond)))
    without_ai = _build(None)
    statuses = {n: a["insight"]["status"] for n, a in with_ai["analyses"].items()}
    assert [n for n, s in statuses.items() if s != "available"] == ["seasonality"]
    assert with_ai["analyses"]["seasonality"]["insight"]["reason"] == "GUARDRAIL_REJECTED"
    assert with_ai["notices"][-1]["code"] == "INSIGHTS_UNAVAILABLE"
    for name, analysis in with_ai["analyses"].items():
        assert analysis["findings"] == without_ai["analyses"][name]["findings"]


def test_with_insights_off_there_is_no_insight_and_no_call() -> None:
    result = _build(None)
    assert all("insight" not in a for a in result["analyses"].values())
    assert result["insights"] == {"requested": False}
