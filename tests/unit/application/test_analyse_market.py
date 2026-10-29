import random
import time
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.application.analyse_market import analyse_market
from app.domain.booking import Booking
from app.domain.errors import InvalidRequest
from app.domain.holidays import build_calendar
from app.domain.period import Period
from tests.unit.booking_factory import calendar_of, make_booking, stay

BOOKING_COUNT = 55_484
TIME_LIMIT_SECONDS = 15.0


def test_all_nine_analyses_are_returned_with_formula_and_limitations() -> None:
    bookings = [stay(date(2024, 1, 1), 7, lead_time=10), stay(date(2024, 1, 4), 2)]
    result = analyse_market(bookings, 2, calendar_of(date(2024, 1, 3)))
    nine = [
        result.lead_time,
        result.holidays,
        result.seasonality,
        result.cancellations,
        result.room_value,
        result.guest_mix,
        result.occupancy,
        result.occupancy_on_holidays,
        result.correlations,
    ]
    assert len(nine) == 9
    assert all(analysis.formula and analysis.limitations for analysis in nine)
    assert result.record_count == 2
    assert result.missing_counts["lead_time"] == 1


def test_occupancy_uses_the_room_count_and_the_period_given() -> None:
    result = analyse_market(
        [stay(date(2024, 1, 1), 7)],
        2,
        calendar_of(date(2024, 1, 3)),
        Period(date(2024, 1, 1), date(2024, 1, 7)),
    )
    assert result.occupancy.overall.share == 0.5
    # the holiday Jan 3 has 1 of 2 room nights taken, as the other days do
    assert result.occupancy_on_holidays.holiday_days.share == 0.5


def test_no_bookings_are_refused() -> None:
    with pytest.raises(InvalidRequest):
        analyse_market([], 1, calendar_of())


def test_a_room_count_below_one_is_refused() -> None:
    with pytest.raises(InvalidRequest):
        analyse_market([make_booking()], 0, calendar_of())


def _generated(count: int) -> list[Booking]:
    rng = random.Random(7)  # noqa: S311 - seeded test data, not security
    first = date(2022, 1, 1)
    markets = ["Online", "Direct", "Groups", "Corporate", "Offline"]
    bookings = []
    for number in range(count):
        arrival = first + timedelta(days=rng.randrange(900))
        lead = rng.randrange(400)
        has_price = rng.random() > 0.02
        bookings.append(
            make_booking(
                booking_id=number,
                is_canceled=rng.random() < 0.3,
                arrival_date=arrival,
                booking_date=arrival - timedelta(days=lead) if rng.random() > 0.01 else None,
                lead_time=lead if rng.random() > 0.01 else None,
                stays_in_weekend_nights=rng.randrange(4),
                stays_in_week_nights=rng.randrange(8),
                adults=rng.randrange(1, 4),
                children=rng.randrange(3),
                babies=rng.randrange(2),
                country=rng.choice(["PRT", "GBR", "FRA", "DEU", "ESP"]),
                market_segment=rng.choice(markets),
                customer_type=rng.choice(["Transient", "Contract", "Group"]),
                deposit_type=rng.choice(["No Deposit", "Non Refund"]),
                booking_changes=rng.randrange(4),
                previous_cancellations=rng.randrange(3),
                required_car_parking_spaces=rng.randrange(2),
                total_of_special_requests=rng.randrange(5),
                price_per_night=Decimal(rng.randrange(3000, 30000)) / 100 if has_price else None,
            )
        )
    return bookings


def test_a_run_of_55484_bookings_finishes_in_a_few_seconds() -> None:
    bookings = _generated(BOOKING_COUNT)
    calendar = build_calendar(2021, 2025)
    started = time.perf_counter()
    result = analyse_market(bookings, 300, calendar)
    elapsed = time.perf_counter() - started
    assert result.record_count == BOOKING_COUNT
    assert elapsed < TIME_LIMIT_SECONDS
