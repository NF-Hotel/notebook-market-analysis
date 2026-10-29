from datetime import date
from decimal import Decimal

from app.domain.analyses.seasonality import analyse_seasonality
from tests.unit.booking_factory import make_booking


def _arrivals() -> list:
    # 2024-01-30 is a Tuesday (ISO week 5, Monday 2024-01-29); 2024-02-05 is a Monday (week 6)
    return [
        make_booking(arrival_date=date(2024, 1, 30), price_per_night=Decimal("100")),
        make_booking(
            arrival_date=date(2024, 1, 31), price_per_night=Decimal("200"), is_canceled=True
        ),
        make_booking(arrival_date=date(2024, 2, 5)),
    ]


def test_arrivals_by_month_with_cancellation_share_and_mean_price() -> None:
    monthly = analyse_seasonality(_arrivals()).arrivals.monthly
    january, february = monthly
    assert (january.figure.group, january.figure.numerator, january.figure.denominator) == (
        "2024-01",
        2,
        3,
    )
    assert (january.cancellation.numerator, january.cancellation.denominator) == (1, 2)
    assert january.mean_price_per_night.value == Decimal("150.0000")
    assert january.mean_price_per_night.count == 2
    assert february.figure.numerator == 1
    assert february.mean_price_per_night.value is None
    assert february.mean_price_per_night.count == 0


def test_months_at_the_edge_of_the_data_are_partial() -> None:
    january, february = analyse_seasonality(_arrivals()).arrivals.monthly
    assert january.partial_period is True  # the data starts on Jan 30
    assert february.partial_period is True  # the data ends on Feb 5


def test_arrivals_by_iso_week() -> None:
    weeks = analyse_seasonality(_arrivals()).arrivals.iso_week
    assert [(w.figure.group, w.figure.numerator) for w in weeks] == [
        ("2024-W05", 2),
        ("2024-W06", 1),
    ]
    assert weeks[0].partial_period is True  # the data starts on the Tuesday of the week


def test_a_whole_month_inside_the_data_is_not_partial() -> None:
    bookings = [
        make_booking(arrival_date=date(2024, 1, 15)),
        make_booking(arrival_date=date(2024, 2, 20)),
        make_booking(arrival_date=date(2024, 3, 10)),
    ]
    february = analyse_seasonality(bookings).arrivals.monthly[1]
    assert february.figure.group == "2024-02"
    assert february.partial_period is False


def test_years_with_fewer_than_twelve_months_are_incomplete() -> None:
    result = analyse_seasonality(_arrivals()).arrivals.incomplete_years
    assert [(y.year, y.months_present) for y in result] == [(2024, 2)]


def test_a_year_with_all_twelve_months_is_complete() -> None:
    bookings = [make_booking(arrival_date=date(2024, month, 15)) for month in range(1, 13)]
    assert analyse_seasonality(bookings).arrivals.incomplete_years == ()


def test_bookings_without_booking_date_are_left_out_and_counted() -> None:
    bookings = [*_arrivals(), make_booking(booking_date=date(2024, 1, 2))]
    measure = analyse_seasonality(bookings).bookings
    assert measure.records_used == 1
    assert measure.records_missing_date == 3
    assert measure.monthly[0].figure.group == "2024-01"
    assert measure.monthly[0].figure.small_sample is True


def test_without_any_date_the_measure_is_empty() -> None:
    measure = analyse_seasonality([make_booking()]).bookings
    assert measure.span is None
    assert measure.monthly == ()
