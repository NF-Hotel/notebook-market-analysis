from datetime import date

from app.domain.analyses.occupancy_on_holidays import analyse_occupancy_on_holidays
from app.domain.period import Period
from tests.unit.booking_factory import calendar_of, stay


def test_occupancy_on_a_holiday_differs_from_occupancy_on_other_days() -> None:
    # Two rooms, period Jan 1 to Jan 6, Jan 3 is the holiday.
    # A: Jan 1 to Jan 5 (5 nights). B: Jan 3 only. Room nights per day: 1, 1, 2, 1, 1, 0.
    bookings = [stay(date(2024, 1, 1), 5), stay(date(2024, 1, 3), 1)]
    result = analyse_occupancy_on_holidays(
        bookings,
        room_count=2,
        calendar=calendar_of(date(2024, 1, 3)),
        period=Period(date(2024, 1, 1), date(2024, 1, 6)),
    )
    # holiday: 2 of 2 * 1 = 100 %; other days: 1 + 1 + 1 + 1 + 0 = 4 of 2 * 5 = 40 %
    assert (result.holiday_days.numerator, result.holiday_days.denominator) == (2, 2)
    assert (result.other_days.numerator, result.other_days.denominator) == (4, 10)
    assert result.holiday_days.share == 1.0
    assert result.other_days.share == 0.4
    assert result.holiday_days.share != result.other_days.share


def test_days_in_years_the_calendar_does_not_cover_are_left_out_and_counted() -> None:
    # One room, nights Dec 31, Jan 1, Jan 2; the calendar covers 2024 only; Jan 3 is a holiday.
    result = analyse_occupancy_on_holidays(
        [stay(date(2023, 12, 31), 3)],
        room_count=1,
        calendar=calendar_of(date(2024, 1, 3)),
        period=Period(date(2023, 12, 31), date(2024, 1, 3)),
    )
    assert result.days_left_out_unavailable_years == 1
    assert (result.holiday_days.numerator, result.holiday_days.denominator) == (0, 1)
    assert (result.other_days.numerator, result.other_days.denominator) == (2, 2)


def test_a_period_without_holidays_has_no_holiday_share() -> None:
    result = analyse_occupancy_on_holidays(
        [stay(date(2024, 1, 1), 1)], 1, calendar_of(date(2024, 5, 1))
    )
    assert result.holiday_days.denominator == 0
    assert result.holiday_days.share is None
    assert result.holiday_days.small_sample is True
    assert result.other_days.share == 1.0


def test_the_period_defaults_to_the_span_of_the_bookings() -> None:
    result = analyse_occupancy_on_holidays(
        [stay(date(2024, 1, 1), 3)], 1, calendar_of(date(2024, 1, 2))
    )
    assert result.period == Period(date(2024, 1, 1), date(2024, 1, 3))
    assert (result.holiday_days.numerator, result.holiday_days.denominator) == (1, 1)
