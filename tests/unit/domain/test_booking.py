from datetime import date
from decimal import Decimal

import pytest

from app.domain.booking import missing_counts
from tests.unit.booking_factory import make_booking


def test_nights_are_weekend_plus_week_nights() -> None:
    assert make_booking(stays_in_weekend_nights=2, stays_in_week_nights=3).nights == 5


def test_a_night_is_taken_from_arrival_to_the_day_before_departure() -> None:
    booking = make_booking(
        arrival_date=date(2024, 1, 30), stays_in_weekend_nights=1, stays_in_week_nights=2
    )
    assert booking.departure_date == date(2024, 2, 2)
    assert booking.last_night == date(2024, 2, 1)


def test_a_stay_of_no_nights_has_no_last_night() -> None:
    booking = make_booking(stays_in_week_nights=0)
    assert booking.last_night is None


@pytest.mark.parametrize(
    ("adults", "children", "babies", "expected"),
    [(2, 1, 1, 4), (2, None, None, 2), (None, 1, None, 1), (None, None, None, None)],
)
def test_total_guests_adds_the_known_parts(
    adults: int | None, children: int | None, babies: int | None, expected: int | None
) -> None:
    booking = make_booking(adults=adults, children=children, babies=babies)
    assert booking.total_guests == expected


def test_estimated_value_is_price_times_nights() -> None:
    booking = make_booking(stays_in_week_nights=3, price_per_night=Decimal("10.50"))
    assert booking.estimated_value == Decimal("31.50")


def test_estimated_value_is_none_without_a_price() -> None:
    assert make_booking().estimated_value is None


def test_missing_counts_count_the_optional_fields_that_are_none() -> None:
    counts = missing_counts([make_booking(lead_time=3), make_booking(meal="BB")])
    assert counts["lead_time"] == 1
    assert counts["meal"] == 1
    assert counts["price_per_night"] == 2
    assert "country" not in counts
