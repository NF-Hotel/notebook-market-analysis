"""Danish public holidays: the entities and the rules that compute them. No I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.errors import InvalidRequest

COUNTRY = "DK"
SOURCE = "computed"
MIN_YEAR = 1900
MAX_YEAR = 2200
# Store Bededag was abolished in 2024.
_LAST_GREAT_PRAYER_DAY_YEAR = 2023


@dataclass(frozen=True)
class HolidayPeriod:
    name: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class HolidayCalendar:
    country: str
    source: str
    first_year: int
    last_year: int
    holidays: tuple[HolidayPeriod, ...]

    def for_year(self, year: int) -> HolidayCalendar:
        """The part of the calendar that starts in ``year``."""
        return HolidayCalendar(
            self.country,
            self.source,
            year,
            year,
            tuple(h for h in self.holidays if h.start_date.year == year),
        )


def validate_years(first_year: int, last_year: int) -> None:
    if first_year > last_year:
        raise InvalidRequest("first_year must not be after last_year")
    if first_year < MIN_YEAR or last_year > MAX_YEAR:
        raise InvalidRequest(f"years must be between {MIN_YEAR} and {MAX_YEAR}")


def easter_sunday(year: int) -> date:
    """Easter Sunday in the Gregorian calendar (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * el) // 451
    month, day = divmod(h + el - 7 * m + 114, 31)
    return date(year, month, day + 1)


def holidays_in_year(year: int) -> list[HolidayPeriod]:
    """The Danish public holidays of one year, in date order."""
    easter = easter_sunday(year)

    def day(name: str, when: date) -> HolidayPeriod:
        return HolidayPeriod(name, when, when)

    found = [
        day("New Year's Day", date(year, 1, 1)),
        day("Maundy Thursday", easter - timedelta(days=3)),
        day("Good Friday", easter - timedelta(days=2)),
        day("Easter Sunday", easter),
        day("Easter Monday", easter + timedelta(days=1)),
        day("Ascension Day", easter + timedelta(days=39)),
        day("Whit Sunday", easter + timedelta(days=49)),
        day("Whit Monday", easter + timedelta(days=50)),
        day("Christmas Day", date(year, 12, 25)),
        day("Second Day of Christmas", date(year, 12, 26)),
    ]
    if year <= _LAST_GREAT_PRAYER_DAY_YEAR:
        found.append(day("Great Prayer Day", easter + timedelta(days=26)))
    return sorted(found, key=lambda h: h.start_date)


def build_calendar(first_year: int, last_year: int) -> HolidayCalendar:
    validate_years(first_year, last_year)
    holidays = tuple(
        h for year in range(first_year, last_year + 1) for h in holidays_in_year(year)
    )
    return HolidayCalendar(COUNTRY, SOURCE, first_year, last_year, holidays)
