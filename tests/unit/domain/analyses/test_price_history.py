from datetime import date

from app.domain.analyses.price_history import (
    OccupancyHistory,
    holidays_in_horizon,
    iso_week_days,
    same_holiday_in,
    week_blocks,
)
from app.domain.holidays import build_calendar
from app.domain.period import Period
from tests.unit.booking_factory import stay


def test_the_holidays_that_start_in_the_horizon_are_listed_in_date_order() -> None:
    calendar = build_calendar(2026, 2027)
    found = holidays_in_horizon(calendar, date(2026, 12, 20), date(2027, 2, 18))
    assert [(h.name, h.start_date) for h in found] == [
        ("Christmas Day", date(2026, 12, 25)),
        ("Second Day of Christmas", date(2026, 12, 26)),
        ("New Year's Day", date(2027, 1, 1)),
    ]


def test_a_moving_holiday_is_found_by_name_in_an_earlier_year() -> None:
    calendar = build_calendar(2024, 2026)
    (easter_2026,) = holidays_in_horizon(calendar, date(2026, 4, 5), date(2026, 4, 5))
    earlier = same_holiday_in(calendar, easter_2026, 2025)
    assert earlier is not None
    assert earlier.start_date == date(2025, 4, 20)


def test_a_holiday_that_the_other_year_does_not_have_gives_none() -> None:
    calendar = build_calendar(2023, 2024)
    prayer_day_2023 = next(h for h in calendar.holidays if h.name == "Great Prayer Day")
    assert same_holiday_in(calendar, prayer_day_2023, 2024) is None


def test_an_iso_week_has_seven_days_from_monday_and_week_53_exists_only_in_some_years() -> None:
    days = iso_week_days(2025, 2)
    assert days is not None
    assert (days[0], days[-1]) == (date(2025, 1, 6), date(2025, 1, 12))
    assert iso_week_days(2025, 53) is None
    assert iso_week_days(2026, 53) is not None


def test_the_horizon_is_cut_at_the_iso_weeks() -> None:
    blocks = week_blocks(date(2026, 11, 11), date(2026, 11, 24))
    assert blocks == [
        Period(date(2026, 11, 11), date(2026, 11, 15)),
        Period(date(2026, 11, 16), date(2026, 11, 22)),
        Period(date(2026, 11, 23), date(2026, 11, 24)),
    ]


def test_the_history_adds_up_room_nights_and_capacity_of_the_days() -> None:
    bookings = [stay(date(2025, 1, 1), 2), stay(date(2025, 1, 2), 1)]
    history = OccupancyHistory(bookings, 4, Period(date(2025, 1, 1), date(2025, 1, 31)))
    year = history.year_of(2025, [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)])
    assert year is not None
    # nights: Jan 1 -> 1, Jan 2 -> 2, Jan 3 -> 0: 3 room nights of 4 * 3 = 12
    assert (year.taken, year.capacity, year.occupancy) == (3, 12, 0.25)


def test_a_day_outside_the_bookings_gives_no_year() -> None:
    period = Period(date(2025, 1, 1), date(2025, 1, 31))
    history = OccupancyHistory([stay(date(2025, 1, 1), 1)], 4, period)
    assert history.year_of(2024, [date(2024, 12, 31), date(2025, 1, 1)]) is None
