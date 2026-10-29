from decimal import Decimal

import pytest

from app.domain.analyses.room_value import analyse_room_value, stay_bucket
from tests.unit.booking_factory import make_booking


@pytest.mark.parametrize(
    ("nights", "bucket"),
    [(1, "1"), (4, "4"), (5, "5-7"), (7, "5-7"), (8, "8+"), (30, "8+")],
)
def test_stay_bucket_boundaries(nights: int, bucket: str) -> None:
    assert stay_bucket(nights) == bucket


def _bookings() -> list:
    return [
        # 2 nights at 50.50 = 101.00
        make_booking(
            stays_in_weekend_nights=1, stays_in_week_nights=1, price_per_night=Decimal("50.50")
        ),
        # no nights: left out
        make_booking(stays_in_week_nights=0, price_per_night=Decimal("10")),
        # 8 nights at 0: counted as a zero price
        make_booking(
            is_canceled=True,
            stays_in_weekend_nights=5,
            stays_in_week_nights=3,
            price_per_night=Decimal("0"),
        ),
        # 1 night, no price
        make_booking(is_canceled=True),
        # 4 nights at 100 = 400
        make_booking(stays_in_week_nights=4, price_per_night=Decimal("100")),
    ]


def test_length_of_stay_buckets_and_total_nights() -> None:
    result = analyse_room_value(_bookings())
    assert result.records_used == 4
    assert result.zero_night_records == 1
    assert result.total_nights == 15
    assert [(f.group, f.numerator, f.denominator) for f in result.length_of_stay] == [
        ("1", 1, 4),
        ("2", 1, 4),
        ("3", 0, 4),
        ("4", 1, 4),
        ("5-7", 0, 4),
        ("8+", 1, 4),
    ]


def test_estimated_value_is_price_times_nights_and_labelled_an_estimate() -> None:
    result = analyse_room_value(_bookings())
    assert result.estimate_notice_code == "ESTIMATE_NOT_REVENUE"
    assert "not revenue" in result.estimate_label
    assert result.overall.total == Decimal("501.00")
    assert result.overall.value_per_booking.count == 3
    assert result.overall.value_per_booking.value == Decimal("167.0000")


def test_missing_and_zero_prices_are_counted() -> None:
    result = analyse_room_value(_bookings())
    assert result.records_without_price == 1
    assert result.zero_price_records == 1


def test_value_by_cancellation_status() -> None:
    canceled, kept = analyse_room_value(_bookings()).by_cancellation_status
    assert (canceled.figure.group, canceled.figure.numerator, canceled.figure.denominator) == (
        "canceled",
        2,
        4,
    )
    assert canceled.total == Decimal("0")
    assert canceled.records_without_price == 1
    assert canceled.zero_price_records == 1
    assert canceled.value_per_booking.value == Decimal("0.0000")
    assert kept.total == Decimal("501.00")
    assert kept.value_per_booking.value == Decimal("250.5000")


def test_without_prices_the_value_is_none_and_nothing_crashes() -> None:
    result = analyse_room_value([make_booking()])
    assert result.overall.value_per_booking.value is None
    assert result.overall.total == Decimal("0")
    assert result.overall.figure.small_sample is True
