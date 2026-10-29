from datetime import date

import pytest

from app.domain.analyses.lead_time import analyse_lead_time, lead_time_band
from tests.unit.booking_factory import make_booking


@pytest.mark.parametrize(
    ("days", "band"),
    [(0, "0-7"), (7, "0-7"), (8, "8-30"), (30, "8-30"), (31, "31-90"), (90, "31-90"), (91, "91+")],
)
def test_lead_time_band_boundaries(days: int, band: str) -> None:
    assert lead_time_band(days) == band


def _bookings() -> list:
    jan, feb = date(2024, 1, 10), date(2024, 2, 10)
    return [
        make_booking(lead_time=5, is_canceled=True, arrival_date=jan, market_segment="Online"),
        make_booking(lead_time=8, arrival_date=jan, market_segment="Online"),
        make_booking(lead_time=30, arrival_date=feb, market_segment="Online"),
        make_booking(lead_time=31, arrival_date=feb, market_segment="Direct"),
        make_booking(lead_time=90, arrival_date=feb),
        make_booking(lead_time=91, arrival_date=feb),
        make_booking(lead_time=None, arrival_date=feb),
    ]


def test_overall_bands_and_median_are_counted_by_hand() -> None:
    result = analyse_lead_time(_bookings())
    # lead times 5, 8, 30, 31, 90, 91: median (30 + 31) / 2
    assert result.records_used == 6
    assert result.records_without_lead_time == 1
    assert result.overall.median_days == 30.5
    assert [(b.group, b.numerator, b.denominator) for b in result.overall.bands] == [
        ("0-7", 1, 6),
        ("8-30", 2, 6),
        ("31-90", 2, 6),
        ("91+", 1, 6),
    ]
    assert result.overall.figure.numerator == 6


def test_split_by_cancellation_status() -> None:
    groups = {g.figure.group: g for g in analyse_lead_time(_bookings()).by_cancellation_status}
    assert groups["canceled"].figure.numerator == 1
    assert groups["canceled"].median_days == 5.0
    assert groups["not_canceled"].figure.numerator == 5
    assert groups["not_canceled"].median_days == 31.0


def test_split_by_arrival_month_is_chronological() -> None:
    months = analyse_lead_time(_bookings()).by_arrival_month
    assert [(g.figure.group, g.figure.numerator, g.median_days) for g in months] == [
        ("2024-01", 2, 6.5),
        ("2024-02", 4, 60.5),
    ]


def test_split_by_market_segment_leaves_out_missing_segments() -> None:
    segments = analyse_lead_time(_bookings()).by_market_segment
    assert [(g.figure.group, g.figure.numerator, g.figure.denominator) for g in segments] == [
        ("Online", 3, 6),
        ("Direct", 1, 6),
    ]
    assert segments[0].median_days == 8.0


def test_without_any_lead_time_nothing_is_calculated_and_nothing_crashes() -> None:
    result = analyse_lead_time([make_booking(), make_booking()])
    assert result.records_used == 0
    assert result.overall.median_days is None
    assert result.overall.figure.small_sample is True
    assert result.by_arrival_month == ()


def test_small_sample_is_set_below_30_records() -> None:
    assert analyse_lead_time(_bookings()).overall.figure.small_sample is True
    many = [make_booking(lead_time=1) for _ in range(30)]
    assert analyse_lead_time(many).overall.figure.small_sample is False


def test_result_names_its_formula_and_limitations() -> None:
    result = analyse_lead_time(_bookings())
    assert result.formula
    assert result.limitations
