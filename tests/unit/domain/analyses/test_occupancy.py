from datetime import date

import pytest

from app.domain.analyses.occupancy import analyse_occupancy, nightly_counts
from app.domain.errors import InvalidRequest
from app.domain.period import Period
from tests.unit.booking_factory import make_booking, stay


def test_one_room_taken_for_the_whole_period_of_two_rooms_is_fifty_percent() -> None:
    # nights 2024-01-01 to 2024-01-07 (departure on the 8th): 7 room nights of 2 * 7 = 14
    bookings = [stay(date(2024, 1, 1), 7)]
    result = analyse_occupancy(
        bookings, room_count=2, period=Period(date(2024, 1, 1), date(2024, 1, 7))
    )
    assert (result.overall.numerator, result.overall.denominator) == (7, 14)
    assert result.overall.share == 0.5
    assert result.over_capacity_days == 0


def test_the_period_defaults_to_the_span_of_the_bookings() -> None:
    result = analyse_occupancy([stay(date(2024, 1, 1), 7)], room_count=2)
    assert result.period == Period(date(2024, 1, 1), date(2024, 1, 7))
    assert result.overall.share == 0.5


def test_the_departure_day_is_not_a_night_taken() -> None:
    # one night on Jan 1; the period is Jan 1 and Jan 2, one room: 1 of 2
    result = analyse_occupancy(
        [stay(date(2024, 1, 1), 1)], 1, Period(date(2024, 1, 1), date(2024, 1, 2))
    )
    assert (result.overall.numerator, result.overall.denominator) == (1, 2)


def test_monthly_occupancy_splits_a_stay_over_the_month_end() -> None:
    # Two rooms. A: nights Jan 30, Jan 31, Feb 1, Feb 2. B: night Feb 1.
    bookings = [stay(date(2024, 1, 30), 4), stay(date(2024, 2, 1), 1)]
    result = analyse_occupancy(bookings, room_count=2)
    january, february = result.monthly
    # January: days 30, 31 -> 1 + 1 = 2 of 2 * 2 = 4; February: days 1, 2 -> 2 + 1 = 3 of 4
    assert (january.group, january.numerator, january.denominator) == ("2024-01", 2, 4)
    assert (february.group, february.numerator, february.denominator) == ("2024-02", 3, 4)
    assert (result.overall.numerator, result.overall.denominator) == (5, 8)


def test_cancelled_bookings_take_no_room_night() -> None:
    bookings = [stay(date(2024, 1, 1), 2), stay(date(2024, 1, 1), 2, is_canceled=True)]
    result = analyse_occupancy(bookings, 1, Period(date(2024, 1, 1), date(2024, 1, 2)))
    assert (result.overall.numerator, result.overall.denominator) == (2, 2)


def test_only_nights_inside_the_given_period_count() -> None:
    result = analyse_occupancy(
        [stay(date(2024, 1, 1), 10)], 1, Period(date(2024, 1, 3), date(2024, 1, 5))
    )
    assert (result.overall.numerator, result.overall.denominator) == (3, 3)


def test_a_booking_outside_the_period_counts_nothing() -> None:
    result = analyse_occupancy(
        [stay(date(2024, 3, 1), 2)], 1, Period(date(2024, 1, 1), date(2024, 1, 3))
    )
    assert result.overall.numerator == 0


def test_over_capacity_is_not_capped_and_is_named_in_the_limitations() -> None:
    bookings = [stay(date(2024, 1, 1), 2), stay(date(2024, 1, 1), 2)]
    result = analyse_occupancy(bookings, 1, Period(date(2024, 1, 1), date(2024, 1, 2)))
    assert (result.overall.numerator, result.overall.denominator) == (4, 2)
    assert result.overall.share == 2.0
    assert result.over_capacity_days == 2
    assert "exceeded room_count" in result.limitations[-1]


def test_small_sample_is_set_when_the_room_nights_of_the_period_are_below_30() -> None:
    assert analyse_occupancy([stay(date(2024, 1, 1), 7)], 2).overall.small_sample is True
    assert analyse_occupancy([stay(date(2024, 1, 1), 30)], 1).overall.small_sample is False


def test_a_stay_of_no_nights_takes_nothing_and_gives_a_period_of_its_arrival_day() -> None:
    result = analyse_occupancy([make_booking(stays_in_week_nights=0)], 1)
    assert result.period == Period(date(2024, 1, 1), date(2024, 1, 1))
    assert result.overall.numerator == 0


def test_nightly_counts_per_day() -> None:
    bookings = [stay(date(2024, 1, 1), 3), stay(date(2024, 1, 2), 1)]
    assert nightly_counts(bookings, Period(date(2024, 1, 1), date(2024, 1, 4))) == [1, 2, 1, 0]


def test_no_bookings_and_no_period_is_refused() -> None:
    with pytest.raises(InvalidRequest):
        analyse_occupancy([], 1)


def test_no_bookings_in_a_given_period_is_empty_occupancy() -> None:
    result = analyse_occupancy([], 3, Period(date(2024, 1, 1), date(2024, 1, 2)))
    assert (result.overall.numerator, result.overall.denominator) == (0, 6)


def test_a_room_count_below_one_is_refused() -> None:
    with pytest.raises(InvalidRequest):
        analyse_occupancy([make_booking()], 0)


def test_a_period_that_ends_before_it_starts_is_refused() -> None:
    with pytest.raises(InvalidRequest):
        Period(date(2024, 1, 2), date(2024, 1, 1))
