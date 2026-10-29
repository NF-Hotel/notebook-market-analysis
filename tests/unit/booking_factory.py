"""Small helpers that build bookings and calendars for the tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.booking import Booking
from app.domain.holidays import HolidayCalendar, HolidayPeriod


def make_booking(**changes: Any) -> Booking:  # noqa: ANN401 - field overrides of any field type
    """A booking of one week night on 2024-01-01; ``changes`` override any field."""
    fields: dict[str, Any] = {
        "booking_id": 1,
        "hotel": "City Hotel",
        "is_canceled": False,
        "arrival_date": date(2024, 1, 1),
        "stays_in_weekend_nights": 0,
        "stays_in_week_nights": 1,
        "country": "PRT",
    }
    fields.update(changes)
    return Booking(**fields)


def stay(arrival: date, nights: int, **changes: Any) -> Booking:  # noqa: ANN401
    """A booking of ``nights`` week nights from ``arrival``."""
    return make_booking(arrival_date=arrival, stays_in_week_nights=nights, **changes)


def calendar_of(*days: date, first_year: int = 2024, last_year: int = 2024) -> HolidayCalendar:
    """A calendar with the given single-day holidays, covering the years given."""
    holidays = tuple(HolidayPeriod("Holiday", day, day) for day in days)
    return HolidayCalendar("DK", "test", first_year, last_year, holidays)


def price(value: str) -> Decimal:
    return Decimal(value)
