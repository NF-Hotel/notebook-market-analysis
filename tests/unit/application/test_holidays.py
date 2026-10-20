from datetime import date

import pytest

from app.application.holidays import HolidayService
from app.domain.errors import InvalidRequest
from app.domain.holidays import HolidayCalendar


class MemoryStore:
    def __init__(self) -> None:
        self.calendar: HolidayCalendar | None = None

    def load(self) -> HolidayCalendar | None:
        return self.calendar

    def save(self, calendar: HolidayCalendar) -> None:
        self.calendar = calendar


def make() -> tuple[HolidayService, MemoryStore]:
    store = MemoryStore()
    return HolidayService(store, today=lambda: date(2026, 6, 1)), store


def test_get_generates_and_stores_a_default_range() -> None:
    service, store = make()
    calendar = service.get()
    assert (calendar.first_year, calendar.last_year) == (2025, 2028)
    assert store.calendar == calendar


def test_get_limits_to_a_year() -> None:
    service, _ = make()
    calendar = service.get(2026)
    assert (calendar.first_year, calendar.last_year) == (2026, 2026)
    assert {h.start_date.year for h in calendar.holidays} == {2026}


def test_update_replaces_the_stored_calendar() -> None:
    service, store = make()
    calendar = service.update(2030, 2031)
    assert store.calendar == calendar
    assert calendar.first_year == 2030


def test_update_with_only_first_year_reaches_at_least_that_year() -> None:
    service, _ = make()
    assert service.update(2040, None).last_year == 2040


def test_update_rejects_reversed_years() -> None:
    service, _ = make()
    with pytest.raises(InvalidRequest):
        service.update(2030, 2029)
