"""Use case: the nine analyses of a list of bookings."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.analyses.cancellations import CancellationAnalysis, analyse_cancellations
from app.domain.analyses.correlations import CorrelationsAnalysis, analyse_correlations
from app.domain.analyses.guest_mix import GuestMixAnalysis, analyse_guest_mix
from app.domain.analyses.holiday_effect import HolidayAnalysis, analyse_holidays
from app.domain.analyses.lead_time import LeadTimeAnalysis, analyse_lead_time
from app.domain.analyses.occupancy import (
    OccupancyAnalysis,
    analyse_occupancy,
    validate_room_count,
)
from app.domain.analyses.occupancy_on_holidays import (
    OccupancyOnHolidaysAnalysis,
    analyse_occupancy_on_holidays,
)
from app.domain.analyses.room_value import RoomValueAnalysis, analyse_room_value
from app.domain.analyses.seasonality import SeasonalityAnalysis, analyse_seasonality
from app.domain.booking import Booking, missing_counts
from app.domain.errors import InvalidRequest
from app.domain.holidays import HolidayCalendar
from app.domain.period import Period


@dataclass(frozen=True, slots=True)
class MarketAnalysis:
    """The result of the nine analyses, with the counts of the data they rest on."""

    record_count: int
    missing_counts: dict[str, int]
    lead_time: LeadTimeAnalysis
    holidays: HolidayAnalysis
    seasonality: SeasonalityAnalysis
    cancellations: CancellationAnalysis
    room_value: RoomValueAnalysis
    guest_mix: GuestMixAnalysis
    occupancy: OccupancyAnalysis
    occupancy_on_holidays: OccupancyOnHolidaysAnalysis
    correlations: CorrelationsAnalysis


def analyse_market(
    bookings: list[Booking],
    room_count: int,
    calendar: HolidayCalendar,
    period: Period | None = None,
) -> MarketAnalysis:
    """Run the nine analyses over ``bookings`` for a hotel of ``room_count`` rooms."""
    if not bookings:
        raise InvalidRequest("at least one booking is needed")
    validate_room_count(room_count)
    return MarketAnalysis(
        record_count=len(bookings),
        missing_counts=missing_counts(bookings),
        lead_time=analyse_lead_time(bookings),
        holidays=analyse_holidays(bookings, calendar),
        seasonality=analyse_seasonality(bookings),
        cancellations=analyse_cancellations(bookings),
        room_value=analyse_room_value(bookings),
        guest_mix=analyse_guest_mix(bookings),
        occupancy=analyse_occupancy(bookings, room_count, period),
        occupancy_on_holidays=analyse_occupancy_on_holidays(bookings, room_count, calendar, period),
        correlations=analyse_correlations(bookings),
    )
