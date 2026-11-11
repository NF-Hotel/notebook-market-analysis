"""The run paths and result schema 1.2 of openapi/market-contract.yaml (MIL-001, task 1)."""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[2]
CONTRACT = ROOT / "openapi" / "market-contract.yaml"
SAMPLE = ROOT / "docs" / "test-data" / "market-analysis-result.json"

RUN_PATHS = {
    "/api/v1/market-analysis/runs": "post",
    "/api/v1/market-analysis/runs/{run_id}": "get",
    "/api/v1/market-analysis/runs/{run_id}/result": "get",
}


def _contract() -> dict[str, Any]:
    return cast("dict[str, Any]", yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))


def _validator(schema_name: str) -> Draft202012Validator:
    contract = _contract()
    schema = {"$ref": f"#/components/schemas/{schema_name}", "components": contract["components"]}
    return Draft202012Validator(schema)


def _figure(group: str, numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "group": group,
        "numerator": numerator,
        "denominator": denominator,
        "small_sample": False,
    }


def _nine_analyses_result() -> dict[str, Any]:
    """The sample of the web application (six analyses) plus what schema 1.1 and 1.2 add."""
    result = cast("dict[str, Any]", json.loads(SAMPLE.read_text(encoding="utf-8")))
    for analysis in result["analyses"].values():
        analysis.setdefault("formula", "Counts divided by the records used.")
        analysis.setdefault("limitations", ["Describes the observed bookings only."])
    period = {"first_date": "2018-07-01", "last_date": "2020-08-31"}
    result["input"]["room_count"] = 100
    result["input"]["period"] = period
    result["analyses"]["occupancy"] = {
        "status": "available",
        "formula": "Room nights taken divided by room_count times the nights of the period.",
        "limitations": ["A booking is counted from arrival to the day before departure."],
        "findings": {
            "room_count": 100,
            "period": period,
            "overall": _figure("all", 50, 100),
            "monthly": [_figure("2018-07", 25, 50)],
        },
    }
    result["analyses"]["occupancy_on_holidays"] = {
        "status": "available",
        "formula": "The same share, on holiday days against other days.",
        "limitations": ["Holidays come from the holiday calendar of the service."],
        "findings": {
            "holiday_days": _figure("holiday", 30, 40),
            "other_days": _figure("other", 20, 60),
        },
    }
    result["analyses"]["correlations"] = {
        "status": "available",
        "formula": "Spearman rank correlation between each numeric field and is_canceled.",
        "limitations": ["A correlation is not a cause."],
        "findings": {
            "method": "spearman",
            "fields": ["lead_time", "is_canceled"],
            "matrix": [[1.0, -1.0], [-1.0, None]],
        },
    }
    result["analyses"]["room_value"]["findings"]["room_revenue"] = _room_revenue()
    result["forecast"] = _forecast()
    result["schema_version"] = "1.2"
    return result


def _room_revenue() -> dict[str, Any]:
    return {
        "status": "available",
        "unit": "price units of the input",
        "limitation": "Before taxes, fees, discounts and extras.",
        "records_used": 3,
        "records_with_price": 2,
        "records_without_price": 1,
        "total": "501.00",
        "mean": "250.5000",
        "small_sample": True,
        "monthly": [{"group": "2024-01", "value": "501.00", "bookings": 2}],
    }


def _forecast() -> dict[str, Any]:
    months = [{"group": "2024-03", "value": "10.00", "low": "8.00", "high": None}]
    measure = {"unit": "bookings", "months": months}
    return {
        "formula": "The mean of the same calendar month of the history.",
        "limitations": ["The seasonal pattern repeats."],
        "history_months": 12,
        "minimum_history_months": 24,
        "history_too_short": True,
        "horizon_months": 6,
        "measures": {"arrivals": measure, "occupancy": measure, "room_revenue": measure},
    }


def test_contract_describes_the_run_paths() -> None:
    paths = _contract()["paths"]
    for path, method in RUN_PATHS.items():
        assert method in paths[path]


def test_every_run_path_needs_the_key() -> None:
    contract = _contract()
    assert contract["security"] == [{"apiKey": []}]
    for path in RUN_PATHS:
        for operation in contract["paths"][path].values():
            assert "security" not in operation


def test_start_run_refuses_with_stable_codes() -> None:
    responses = _contract()["paths"]["/api/v1/market-analysis/runs"]["post"]["responses"]
    assert set(responses) == {"202", "400", "401", "409"}


def test_result_schema_version_is_1_2_or_1_3() -> None:
    schema = _contract()["components"]["schemas"]["RunResult"]
    assert schema["properties"]["schema_version"]["enum"] == ["1.2", "1.3"]


def test_sample_result_with_nine_analyses_is_valid() -> None:
    _validator("RunResult").validate(_nine_analyses_result())


def test_result_without_one_of_the_nine_analyses_is_invalid() -> None:
    result = _nine_analyses_result()
    del result["analyses"]["correlations"]
    assert not _validator("RunResult").is_valid(result)


def test_result_with_another_schema_version_is_invalid() -> None:
    result = copy.deepcopy(_nine_analyses_result())
    result["schema_version"] = "1.1"
    assert not _validator("RunResult").is_valid(result)


def test_result_without_room_revenue_or_forecast_is_invalid() -> None:
    no_revenue = _nine_analyses_result()
    del no_revenue["analyses"]["room_value"]["findings"]["room_revenue"]
    no_forecast = _nine_analyses_result()
    del no_forecast["forecast"]
    assert not _validator("RunResult").is_valid(no_revenue)
    assert not _validator("RunResult").is_valid(no_forecast)


def test_forecast_of_more_than_six_months_is_invalid() -> None:
    result = _nine_analyses_result()
    result["forecast"]["horizon_months"] = 7
    assert not _validator("RunResult").is_valid(result)


def test_correlation_outside_minus_one_and_one_is_invalid() -> None:
    result = _nine_analyses_result()
    result["analyses"]["correlations"]["findings"]["matrix"] = [[1.5]]
    assert not _validator("RunResult").is_valid(result)


def _request() -> dict[str, Any]:
    booking = {
        "booking_id": 1,
        "hotel": "City Hotel",
        "is_canceled": False,
        "arrival_date": "2019-07-01",
        "stays_in_weekend_nights": 1,
        "stays_in_week_nights": 2,
        "country": "PRT",
    }
    return {"room_count": 100, "bookings": [booking]}


def test_valid_run_request() -> None:
    _validator("RunRequest").validate(_request())


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(bookings=[]),
        lambda r: r.update(room_count=0),
        lambda r: r.pop("room_count"),
        lambda r: r["bookings"][0].update(is_canceled="no"),
        lambda r: r["bookings"][0].update(unknown_field=1),
        lambda r: r["bookings"][0].pop("country"),
    ],
    ids=["empty", "no-rooms", "room-count-missing", "wrong-type", "unknown-field", "no-country"],
)
def test_invalid_run_request(change: Callable[[dict[str, Any]], object]) -> None:
    request = _request()
    change(request)
    assert not _validator("RunRequest").is_valid(request)


PRICE_SAMPLE = ROOT / "docs" / "test-data" / "price-suggestions-sample.json"


def test_price_suggestions_sample_is_valid() -> None:
    sample = json.loads(PRICE_SAMPLE.read_text(encoding="utf-8"))
    _validator("PriceSuggestions").validate(sample)


def test_run_result_with_price_suggestions_and_schema_1_3_is_valid() -> None:
    result = _nine_analyses_result()
    result["schema_version"] = "1.3"
    result["price_suggestions"] = json.loads(PRICE_SAMPLE.read_text(encoding="utf-8"))
    _validator("RunResult").validate(result)


def test_pricing_block_of_the_request_may_be_empty_and_refuses_unknown_fields() -> None:
    request = _request()
    request["pricing"] = {}
    _validator("RunRequest").validate(request)
    request["pricing"] = {"surcharge": 20}
    assert not _validator("RunRequest").is_valid(request)


def test_a_price_suggestion_needs_its_figures_and_an_explanation() -> None:
    sample = json.loads(PRICE_SAMPLE.read_text(encoding="utf-8"))
    del sample["suggestions"][0]["history"]
    assert not _validator("PriceSuggestions").is_valid(sample)
