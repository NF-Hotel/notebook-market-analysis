from datetime import date

import pytest

from app.domain.errors import InvalidRequest
from app.domain.holidays import build_calendar, easter_sunday, holidays_in_year


@pytest.mark.parametrize(
    ("year", "expected"),
    [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2026, date(2026, 4, 5))],
)
def test_easter_sunday(year: int, expected: date) -> None:
    assert easter_sunday(year) == expected


def test_holidays_2025_follow_easter() -> None:
    found = {h.name: h.start_date for h in holidays_in_year(2025)}
    assert found["Good Friday"] == date(2025, 4, 18)
    assert found["Ascension Day"] == date(2025, 5, 29)
    assert found["Whit Monday"] == date(2025, 6, 9)
    assert "Great Prayer Day" not in found


def test_great_prayer_day_exists_until_2023() -> None:
    found = {h.name: h.start_date for h in holidays_in_year(2023)}
    assert found["Great Prayer Day"] == date(2023, 5, 5)


def test_calendar_is_sorted_and_spans_the_years() -> None:
    calendar = build_calendar(2025, 2026)
    dates = [h.start_date for h in calendar.holidays]
    assert dates == sorted(dates)
    assert {d.year for d in dates} == {2025, 2026}


@pytest.mark.parametrize("years", [(2026, 2025), (1800, 1801), (2100, 2300)])
def test_invalid_years_are_rejected(years: tuple[int, int]) -> None:
    with pytest.raises(InvalidRequest):
        build_calendar(*years)
