from datetime import date

from app.domain.analyses.holiday_effect import HolidayComparison, analyse_holidays
from tests.unit.booking_factory import calendar_of, make_booking

# 2024-01-10 is a Wednesday; the span of the arrivals is 2024-01-01 to 2024-01-21 (21 days).
HOLIDAY = date(2024, 1, 10)


def _arrivals() -> list:
    days = [
        (date(2024, 1, 1), False),
        (date(2024, 1, 3), False),
        (HOLIDAY, False),
        (HOLIDAY, False),
        (HOLIDAY, True),
        (date(2024, 1, 17), False),
        (date(2024, 1, 17), True),
        (date(2024, 1, 21), False),
    ]
    return [make_booking(arrival_date=day, is_canceled=cancelled) for day, cancelled in days]


def _comparison(
    comparisons: tuple[HolidayComparison, ...], kind: str, window: int
) -> HolidayComparison:
    return next(c for c in comparisons if c.day_kind == kind and c.window_days == window)


def test_arrivals_on_the_holiday_are_counted_per_holiday_day() -> None:
    measure = analyse_holidays(_arrivals(), calendar_of(HOLIDAY)).arrival_date
    assert measure.holiday is not None
    group = measure.holiday.group
    assert (group.figure.numerator, group.figure.denominator) == (3, 1)
    assert group.mean_per_day == 3.0
    assert group.figure.small_sample is True
    assert group.cancellation is not None
    assert (group.cancellation.numerator, group.cancellation.denominator) == (1, 3)


def test_baseline_is_the_same_weekday_on_other_days() -> None:
    measure = analyse_holidays(_arrivals(), calendar_of(HOLIDAY)).arrival_date
    assert measure.holiday is not None
    baseline = measure.holiday.baseline
    # Wednesdays that are not holidays: Jan 3 (1 arrival) and Jan 17 (2 arrivals)
    assert (baseline.figure.numerator, baseline.figure.denominator) == (3, 2)
    assert baseline.mean_per_day == 1.5
    assert baseline.cancellation is not None
    assert (baseline.cancellation.numerator, baseline.cancellation.denominator) == (1, 3)


def test_window_of_one_day_before_is_the_tuesday_and_after_is_the_thursday() -> None:
    windows = analyse_holidays(_arrivals(), calendar_of(HOLIDAY)).arrival_date.windows
    before = _comparison(windows, "before", 1)
    after = _comparison(windows, "after", 1)
    assert (before.group.figure.numerator, before.group.figure.denominator) == (0, 1)
    assert (after.group.figure.numerator, after.group.figure.denominator) == (0, 1)
    # Tuesdays outside the window: Jan 2, Jan 16 -> 2 days with no arrivals
    assert (before.baseline.figure.numerator, before.baseline.figure.denominator) == (0, 2)


def test_window_of_three_days_before_holds_the_seventh_to_the_ninth() -> None:
    windows = analyse_holidays(_arrivals(), calendar_of(HOLIDAY)).arrival_date.windows
    before = _comparison(windows, "before", 3)
    assert before.group.figure.denominator == 3
    assert [c.window_days for c in windows] == [1, 1, 3, 3, 7, 7]


def test_without_booking_dates_that_measure_is_empty_and_counted() -> None:
    result = analyse_holidays(_arrivals(), calendar_of(HOLIDAY))
    assert result.booking_date.span is None
    assert result.booking_date.holiday is None
    assert result.booking_date.records_missing_date == 8


def test_booking_dates_are_counted_without_a_cancellation_share() -> None:
    bookings = [
        make_booking(booking_date=date(2024, 1, 10)),
        make_booking(booking_date=date(2024, 1, 11)),
        make_booking(booking_date=date(2024, 1, 17)),
        make_booking(),
    ]
    measure = analyse_holidays(bookings, calendar_of(HOLIDAY)).booking_date
    assert measure.records_missing_date == 1
    assert measure.holiday is not None
    assert measure.holiday.group.figure.numerator == 1
    assert measure.holiday.group.cancellation is None
    # span Jan 10 to Jan 17: Wednesday baseline is Jan 17 with one booking
    assert (
        measure.holiday.baseline.figure.numerator,
        measure.holiday.baseline.figure.denominator,
    ) == (1, 1)


def test_dates_in_years_the_calendar_does_not_cover_are_left_out() -> None:
    bookings = [make_booking(arrival_date=date(2023, 12, 30)), make_booking(arrival_date=HOLIDAY)]
    measure = analyse_holidays(bookings, calendar_of(HOLIDAY)).arrival_date
    assert measure.years_unavailable == (2023,)
    assert measure.records_left_out_unavailable_years == 1
    assert measure.records_used == 1
    assert measure.holiday is not None
    assert (measure.holiday.group.figure.numerator, measure.holiday.group.figure.denominator) == (
        1,
        1,
    )
