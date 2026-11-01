from datetime import date
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


def _revenue_bookings() -> list:
    return [
        # January: 2 nights at 50.50 = 101.00 and 4 nights at 100 = 400.00
        make_booking(
            arrival_date=date(2024, 1, 10),
            stays_in_weekend_nights=1,
            stays_in_week_nights=1,
            price_per_night=Decimal("50.50"),
        ),
        make_booking(
            arrival_date=date(2024, 1, 20),
            stays_in_week_nights=4,
            price_per_night=Decimal("100"),
        ),
        # February: 3 nights at 80 = 240.00, and 1 night without a price (left out, counted)
        make_booking(
            arrival_date=date(2024, 2, 5), stays_in_week_nights=3, price_per_night=Decimal("80")
        ),
        make_booking(arrival_date=date(2024, 2, 6)),
        # cancelled: 5 nights at 200 is not revenue
        make_booking(
            arrival_date=date(2024, 2, 7),
            is_canceled=True,
            stays_in_week_nights=5,
            price_per_night=Decimal("200"),
        ),
        # no nights: left out
        make_booking(
            arrival_date=date(2024, 2, 8), stays_in_week_nights=0, price_per_night=Decimal("10")
        ),
        # March: 2 nights at a price of 0 counts as a booking with a price
        make_booking(
            arrival_date=date(2024, 3, 1), stays_in_week_nights=2, price_per_night=Decimal("0")
        ),
    ]


def test_room_revenue_is_the_total_and_mean_of_the_bookings_that_are_not_cancelled() -> None:
    revenue = analyse_room_value(_revenue_bookings()).room_revenue
    # 101.00 + 400.00 + 240.00 + 0 = 741.00 over 4 priced bookings: 185.25
    assert revenue.total == Decimal("741.00")
    assert revenue.per_booking.count == 4
    assert revenue.per_booking.value == Decimal("185.2500")
    assert revenue.records_used == 5  # four priced bookings and the one without a price
    assert revenue.records_without_price == 1


def test_room_revenue_has_a_value_for_each_month_of_arrival() -> None:
    monthly = analyse_room_value(_revenue_bookings()).room_revenue.monthly
    assert [(m.month, m.total, m.bookings) for m in monthly] == [
        ("2024-01", Decimal("501.00"), 2),
        ("2024-02", Decimal("240.00"), 1),
        ("2024-03", Decimal("0"), 1),
    ]


def test_room_revenue_states_that_it_is_before_taxes_fees_discounts_and_extras() -> None:
    result = analyse_room_value(_revenue_bookings())
    for word in ("taxes", "fees", "discounts", "extras", "currency"):
        assert word in result.room_revenue.limitation
    assert result.room_revenue.limitation in result.limitations


def test_the_old_estimate_is_unchanged_by_room_revenue() -> None:
    result = analyse_room_value(_revenue_bookings())
    # The estimate counts the cancelled booking: 741.00 + 5 x 200 = 1741.00 over 5 priced stays.
    assert result.overall.total == Decimal("1741.00")
    assert result.overall.value_per_booking.value == Decimal("348.2000")
    assert result.records_without_price == 1
    assert result.zero_night_records == 1
    assert result.estimate_notice_code == "ESTIMATE_NOT_REVENUE"


def test_room_revenue_without_prices_is_zero_and_has_no_mean() -> None:
    revenue = analyse_room_value([make_booking()]).room_revenue
    assert (revenue.total, revenue.per_booking.value, revenue.monthly) == (Decimal("0"), None, ())
    assert (revenue.records_used, revenue.records_without_price) == (1, 1)
