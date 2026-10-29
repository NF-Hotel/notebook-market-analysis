"""The booking: one reservation as the web application sends it."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Booking:
    """One booking. An optional field that is ``None`` is missing, not zero."""

    booking_id: int
    hotel: str
    is_canceled: bool
    arrival_date: date
    stays_in_weekend_nights: int
    stays_in_week_nights: int
    country: str
    lead_time: int | None = None
    booking_date: date | None = None
    adults: int | None = None
    children: int | None = None
    babies: int | None = None
    meal: str | None = None
    market_segment: str | None = None
    is_repeated_guest: bool | None = None
    previous_cancellations: int | None = None
    assigned_room_type: str | None = None
    booking_changes: int | None = None
    deposit_type: str | None = None
    customer_type: str | None = None
    required_car_parking_spaces: int | None = None
    total_of_special_requests: int | None = None
    price_per_night: Decimal | None = None

    @property
    def nights(self) -> int:
        return self.stays_in_weekend_nights + self.stays_in_week_nights

    @property
    def departure_date(self) -> date:
        return self.arrival_date + timedelta(days=self.nights)

    @property
    def last_night(self) -> date | None:
        """The last night taken: the day before departure; ``None`` for a stay of no nights."""
        if self.nights == 0:
            return None
        return self.departure_date - timedelta(days=1)

    @property
    def total_guests(self) -> int | None:
        """Adults, children and babies together; ``None`` when none of the three is known."""
        parts = (self.adults, self.children, self.babies)
        if all(part is None for part in parts):
            return None
        return sum(part or 0 for part in parts)

    @property
    def estimated_value(self) -> Decimal | None:
        """Price per night times nights: an estimate, not revenue. ``None`` without a price."""
        if self.price_per_night is None:
            return None
        return self.price_per_night * self.nights


_REQUIRED_FIELDS = frozenset(
    {
        "booking_id",
        "hotel",
        "is_canceled",
        "arrival_date",
        "stays_in_weekend_nights",
        "stays_in_week_nights",
        "country",
    }
)
OPTIONAL_FIELDS: tuple[str, ...] = tuple(
    f.name for f in fields(Booking) if f.name not in _REQUIRED_FIELDS
)


def missing_counts(bookings: list[Booking]) -> dict[str, int]:
    """How many bookings lack each optional field."""
    return {
        name: sum(1 for booking in bookings if getattr(booking, name) is None)
        for name in OPTIONAL_FIELDS
    }
