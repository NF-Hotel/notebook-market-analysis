import json
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator

from app.application.analyse_market import analyse_market
from app.application.documents import JsonObject
from app.application.insights import UnconfiguredInsightProvider
from app.application.market_result import build_market_result, content_sha256
from app.domain.booking import Booking
from app.domain.holidays import build_calendar
from tests.unit.booking_factory import make_booking
from tests.unit.run_fakes import RecordingInsightProvider

CONTRACT = Path(__file__).parents[3] / "openapi" / "market-contract.yaml"
GENERATED_AT = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)  # noqa: UP017
RESULT_ID = "5b3f0e1a-0000-4000-8000-0000000000a1"
NINE = {
    "lead_time",
    "holidays",
    "seasonality",
    "cancellations",
    "room_value",
    "guest_mix",
    "occupancy",
    "occupancy_on_holidays",
    "correlations",
}


def _validator() -> Draft202012Validator:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    schema = {"$ref": "#/components/schemas/RunResult", "components": contract["components"]}
    return Draft202012Validator(schema)


def _bookings(count: int = 300) -> list[Booking]:
    rng = random.Random(3)  # noqa: S311 - seeded test data
    result = []
    for number in range(count):
        arrival = date(2023, 1, 1) + timedelta(days=rng.randrange(700))
        lead = rng.randrange(200)
        result.append(
            make_booking(
                booking_id=number,
                is_canceled=rng.random() < 0.3,
                arrival_date=arrival,
                booking_date=arrival - timedelta(days=lead),
                lead_time=lead,
                stays_in_weekend_nights=rng.randrange(3),
                stays_in_week_nights=rng.randrange(6),
                adults=rng.randrange(1, 4),
                children=rng.randrange(2),
                babies=0,
                meal=rng.choice(["BB", "HB"]),
                country=rng.choice(["PRT", "GBR", "FRA"]),
                market_segment=rng.choice(["Online", "Direct"]),
                is_repeated_guest=rng.random() < 0.1,
                customer_type=rng.choice(["Transient", "Contract"]),
                deposit_type="No Deposit",
                assigned_room_type=rng.choice(["A", "B"]),
                booking_changes=rng.randrange(3),
                previous_cancellations=0,
                required_car_parking_spaces=rng.randrange(2),
                total_of_special_requests=rng.randrange(4),
                price_per_night=Decimal(rng.randrange(5000, 20000)) / 100,
            )
        )
    return result


def _build(bookings: list[Booking], insights: bool | None = True) -> JsonObject:
    calendar = build_calendar(2022, 2026)
    analysis = analyse_market(bookings, 20, calendar)
    provider = None
    if insights is not None:
        provider = RecordingInsightProvider() if insights else UnconfiguredInsightProvider()
    return build_market_result(analysis, bookings, calendar, RESULT_ID, GENERATED_AT, provider)


def test_the_result_validates_against_the_contract() -> None:
    _validator().validate(_build(_bookings()))


def test_the_result_validates_without_insights() -> None:
    _validator().validate(_build(_bookings(), insights=None))


def test_the_result_validates_with_missing_optional_values() -> None:
    _validator().validate(_build([make_booking()]))


def test_the_envelope_holds_the_nine_analyses_and_the_input() -> None:
    bookings = _bookings()
    result = _build(bookings)
    assert result["schema_version"] == "1.1"
    assert result["result_id"] == RESULT_ID
    assert result["generated_at"] == "2026-05-01T08:00:00+00:00"
    assert set(result["analyses"]) == NINE
    assert result["input"]["record_count"] == 300
    assert result["input"]["room_count"] == 20
    assert result["input"]["content_sha256"] == content_sha256(bookings)
    assert result["data_quality"]["record_count"] == 300
    for analysis in result["analyses"].values():
        assert analysis["formula"]
        assert analysis["limitations"]
        assert analysis["status"] == "available"


def test_the_result_is_the_same_for_the_same_input() -> None:
    first = json.dumps(_build(_bookings()), sort_keys=True)
    second = json.dumps(_build(_bookings()), sort_keys=True)
    assert first == second


def test_the_result_is_plain_json_without_nan() -> None:
    json.dumps(_build(_bookings()), allow_nan=False)


def test_the_hash_follows_the_bookings() -> None:
    bookings = _bookings(5)
    assert content_sha256(bookings) == content_sha256(list(bookings))
    assert content_sha256(bookings) != content_sha256(bookings[:4])
    assert len(content_sha256(bookings)) == 64


def test_the_free_text_is_in_the_findings() -> None:
    analyses = _build(_bookings())["analyses"]
    assert "median lead time" in analyses["lead_time"]["findings"]["overall"]["summary"]
    arrivals = analyses["holidays"]["findings"]["arrival_date"]
    assert arrivals["holiday_days"]["statement"].startswith("Mean arrivals per day was")
    assert "observed association" in arrivals["holiday_days"]["statement"]
    assert analyses["seasonality"]["findings"]["note"]
    assert "ISO weeks" in analyses["seasonality"]["findings"]["arrivals"]["summary"]
    assert analyses["cancellations"]["findings"]["note"]
    groups = analyses["room_value"]["findings"]["estimated_value"]["groups"]
    assert "not realized revenue" in groups[0]["summary"]
    assert analyses["guest_mix"]["findings"]["note"]
    assert analyses["occupancy"]["findings"]["summary"].startswith("Occupancy was")


def test_a_small_group_of_guest_mix_has_no_comparison() -> None:
    bookings = [make_booking(booking_id=i, meal="BB") for i in range(2)]
    group = _build(bookings)["analyses"]["guest_mix"]["findings"]["distributions"]["meal"][
        "groups"
    ][0]
    assert group["comparison"]["status"] == "omitted_small_sample"
    assert "small sample of 2 records" in group["comparison"]["statement"]


def test_occupancy_of_one_room_of_two_is_fifty_percent() -> None:
    bookings = [make_booking(stays_in_week_nights=7)]
    calendar = build_calendar(2024, 2024)
    analysis = analyse_market(bookings, 2, calendar)
    result = build_market_result(analysis, bookings, calendar, RESULT_ID, GENERATED_AT, None)
    overall = result["analyses"]["occupancy"]["findings"]["overall"]
    assert (overall["numerator"], overall["denominator"]) == (7, 14)
    assert "50.0 %" in result["analyses"]["occupancy"]["findings"]["summary"]


def test_an_analysis_without_data_is_unavailable_with_a_notice() -> None:
    result = _build([make_booking()], insights=None)
    assert result["analyses"]["lead_time"]["status"] == "unavailable"
    assert result["analyses"]["lead_time"]["reason"] == "NO_LEAD_TIME"
    assert result["analyses"]["room_value"]["reason"] == "NO_PRICE"
    assert result["status"] == "completed_with_warnings"
    assert result["notices"][0]["code"] == "ANALYSES_UNAVAILABLE"


def test_correlations_are_inside_minus_one_and_one() -> None:
    matrix = cast(
        "list[list[Any]]", _build(_bookings())["analyses"]["correlations"]["findings"]["matrix"]
    )
    values = [v for row in matrix for v in row if v is not None]
    assert values
    assert all(-1.0 <= v <= 1.0 for v in values)


@pytest.mark.parametrize("insights", [True, False])
def test_the_insight_key_follows_the_request(insights: bool) -> None:
    result = _build(_bookings(5), insights=insights if insights else None)
    assert all(("insight" in a) is insights for a in result["analyses"].values())
