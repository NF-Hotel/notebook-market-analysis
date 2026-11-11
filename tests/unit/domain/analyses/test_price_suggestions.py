from datetime import date

import pytest

from app.domain.analyses.price_suggestions import (
    PriceSuggestion,
    PriceSuggestionSet,
    PricingSettings,
    suggest_prices,
)
from app.domain.booking import Booking
from app.domain.errors import InvalidRequest
from app.domain.holidays import build_calendar
from app.domain.period import Period
from tests.unit.booking_factory import stay

DATA = Period(date(2024, 1, 1), date(2025, 12, 31))
CALENDAR = build_calendar(2024, 2027)
AS_OF = date(2026, 12, 20)  # the horizon runs to 2027-02-18


def rooms(count: int, arrival: date, nights: int = 1) -> list[Booking]:
    return [stay(arrival, nights, booking_id=i) for i in range(count)]


def christmas(taken_2024: int, taken_2025: int) -> list[Booking]:
    return rooms(taken_2024, date(2024, 12, 25)) + rooms(taken_2025, date(2025, 12, 25))


def suggest(bookings: list[Booking], **settings: object) -> PriceSuggestionSet:
    return suggest_prices(
        bookings,
        room_count=20,
        calendar=CALENDAR,
        settings=PricingSettings(AS_OF, **settings),  # type: ignore[arg-type]
        period=DATA,
    )


def on(result: PriceSuggestionSet, first: date) -> list[PriceSuggestion]:
    return [s for s in result.suggestions if s.first_date == first]


def test_a_holiday_with_85_percent_in_two_earlier_years_gets_a_surcharge_for_every_size() -> None:
    result = suggest(christmas(17, 17))
    (found,) = on(result, date(2026, 12, 25))
    assert (found.room_size, found.change, found.percent, found.reason) == (
        "all",
        "surcharge",
        "20",
        "holiday",
    )
    assert found.holiday == "Christmas Day"
    assert [(y.year, y.taken, y.capacity) for y in found.history] == [
        (2024, 17, 20),
        (2025, 17, 20),
    ]


def test_exactly_the_high_threshold_gives_a_surcharge_and_a_hair_above_it_does_not() -> None:
    bookings = christmas(16, 16)  # 80 percent
    assert on(suggest(bookings), date(2026, 12, 25))
    assert not on(suggest(bookings, high_occupancy_threshold="0.801"), date(2026, 12, 25))


def test_the_occupancy_of_the_years_is_pooled_not_averaged_by_year() -> None:
    # 20 of 20 in 2024 and 12 of 20 in 2025: 32 of 40 = 80 percent
    assert on(suggest(christmas(20, 12)), date(2026, 12, 25))


def test_a_week_with_low_history_gets_a_discount_for_single_rooms_only() -> None:
    # ISO week 2: 2024-01-08..14 and 2025-01-06..12, 7 of 140 room nights in each year
    bookings = rooms(1, date(2024, 1, 8), 7) + rooms(1, date(2025, 1, 6), 7)
    found = on(suggest(bookings), date(2027, 1, 11))
    assert [(s.room_size, s.change, s.percent, s.reason, s.last_date) for s in found] == [
        ("single", "discount", "15", "low_history", date(2027, 1, 17))
    ]
    assert found[0].threshold == "0.40"


def test_a_discount_is_suggested_for_each_size_that_qualifies() -> None:
    result = suggest([], discount_room_sizes=("single", "double"))
    assert {s.room_size for s in on(result, date(2027, 1, 11))} == {"single", "double"}


def test_a_middle_occupancy_gives_no_suggestion() -> None:
    assert not on(suggest(christmas(10, 10)), date(2026, 12, 25))  # 50 percent


def test_too_few_earlier_years_give_no_suggestion_and_are_listed() -> None:
    result = suggest(christmas(17, 17), min_history_years=3)
    assert not on(result, date(2026, 12, 25))
    missing = [m for m in result.not_enough_history if m.first_date == date(2026, 12, 25)]
    assert [(m.holiday, m.years_found) for m in missing] == [("Christmas Day", 2)]


def test_a_year_that_is_not_in_the_bookings_does_not_count() -> None:
    result = suggest_prices(
        rooms(17, date(2025, 12, 25)),
        20,
        CALENDAR,
        PricingSettings(AS_OF),
        period=Period(date(2025, 1, 1), date(2025, 12, 31)),
    )
    missing = [m for m in result.not_enough_history if m.first_date == date(2026, 12, 25)]
    assert [m.years_found for m in missing] == [1]


def test_a_moving_holiday_is_judged_on_its_own_dates_in_earlier_years() -> None:
    # Easter Sunday: 2024-03-31 and 2025-04-20, 18 of 20 rooms each; 2026-04-05 is in the horizon
    bookings = rooms(18, date(2024, 3, 31)) + rooms(18, date(2025, 4, 20))
    result = suggest_prices(
        bookings,
        20,
        CALENDAR,
        PricingSettings(date(2026, 3, 30), horizon_days=14),
        period=DATA,
    )
    (found,) = on(result, date(2026, 4, 5))
    assert (found.holiday, found.change) == ("Easter Sunday", "surcharge")


def test_the_days_of_a_holiday_are_left_out_of_the_week_suggestions() -> None:
    result = suggest([])  # no bookings: every period has 0 percent and gets a discount
    weeks = [s for s in result.suggestions if s.holiday is None]
    monday = [s for s in weeks if s.first_date == date(2026, 12, 21)]
    assert {s.last_date for s in monday} == {date(2026, 12, 24)}
    assert all(not (s.first_date <= date(2026, 12, 25) <= s.last_date) for s in weeks)


def test_no_suggestion_starts_before_the_date_or_ends_after_the_horizon() -> None:
    result = suggest([])
    assert all(
        s.first_date >= AS_OF and s.last_date <= date(2027, 2, 18) for s in result.suggestions
    )
    assert result.as_of == AS_OF
    assert result.horizon_end == date(2027, 2, 18)


def test_the_same_input_gives_the_same_suggestions() -> None:
    bookings = christmas(17, 17) + rooms(1, date(2024, 1, 8), 7)
    assert suggest(bookings) == suggest(list(reversed(bookings)))


@pytest.mark.parametrize(
    "settings",
    [
        {"horizon_days": 6},
        {"horizon_days": 121},
        {"high_occupancy_threshold": "0.3", "low_occupancy_threshold": "0.4"},
        {"high_occupancy_threshold": "1.1"},
        {"surcharge_percent": "0"},
        {"discount_percent": "100"},
        {"min_history_years": 0},
    ],
)
def test_settings_out_of_range_are_refused(settings: dict[str, object]) -> None:
    with pytest.raises(InvalidRequest):
        PricingSettings(AS_OF, **settings)  # type: ignore[arg-type]
