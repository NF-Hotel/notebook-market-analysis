"""A closed range of days."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.errors import InvalidRequest


@dataclass(frozen=True, slots=True)
class Period:
    first_date: date
    last_date: date

    def __post_init__(self) -> None:
        if self.first_date > self.last_date:
            raise InvalidRequest("period first_date must not be after last_date")

    @property
    def days(self) -> int:
        return (self.last_date - self.first_date).days + 1

    def dates(self) -> list[date]:
        return [self.first_date + timedelta(days=i) for i in range(self.days)]


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"
