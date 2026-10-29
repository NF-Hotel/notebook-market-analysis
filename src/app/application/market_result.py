"""Builds the result document of a run (result schema 1.1) from the nine analyses.

The function is deterministic: the id and the time of the result are passed in.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from app.application.analyse_market import MarketAnalysis
from app.application.documents import JsonObject
from app.application.findings import (
    AVAILABLE,
    UNAVAILABLE,
    cancellations_findings,
    correlations_findings,
    date_range_data,
    guest_mix_findings,
    holidays_findings,
    lead_time_findings,
    occupancy_findings,
    occupancy_on_holidays_findings,
    room_value_findings,
    seasonality_findings,
)
from app.application.ports.insight_provider import InsightProvider
from app.domain.booking import OPTIONAL_FIELDS, Booking
from app.domain.holidays import HolidayCalendar

SCHEMA_VERSION = "1.1"
INPUT_SOURCE = "supplied"
INPUT_REFERENCE = "request-body"
NO_LEAD_TIME = "NO_LEAD_TIME"
NO_PRICE = "NO_PRICE"
INSIGHTS_UNAVAILABLE = "INSIGHTS_UNAVAILABLE"
ANALYSES_UNAVAILABLE = "ANALYSES_UNAVAILABLE"
_BOOKING_FIELDS = (
    "booking_id",
    "hotel",
    "is_canceled",
    "arrival_date",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
    "country",
    *OPTIONAL_FIELDS,
)


def content_sha256(bookings: list[Booking]) -> str:
    """A hash of the bookings as posted, in the order posted."""
    rows = [[getattr(b, name) for name in _BOOKING_FIELDS] for b in bookings]
    text = json.dumps(rows, default=str, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _analysis(findings: JsonObject, formula: str, limitations: tuple[str, ...]) -> JsonObject:
    return {
        "status": AVAILABLE,
        "reason": None,
        "formula": formula,
        "limitations": list(limitations),
        "findings": findings,
    }


def _unavailable(analysis: JsonObject, reason: str) -> JsonObject:
    return {**analysis, "status": UNAVAILABLE, "reason": reason}


def _analyses(result: MarketAnalysis, calendar: HolidayCalendar) -> dict[str, JsonObject]:
    lead_time = _analysis(
        lead_time_findings(result.lead_time), result.lead_time.formula, result.lead_time.limitations
    )
    if result.lead_time.records_used == 0:
        lead_time = _unavailable(lead_time, NO_LEAD_TIME)
    room_value = _analysis(
        room_value_findings(result.room_value),
        result.room_value.formula,
        result.room_value.limitations,
    )
    if result.room_value.overall.value_per_booking.count == 0:
        room_value = _unavailable(room_value, NO_PRICE)
    return {
        "lead_time": lead_time,
        "holidays": _analysis(
            holidays_findings(result.holidays, calendar),
            result.holidays.formula,
            result.holidays.limitations,
        ),
        "seasonality": _analysis(
            seasonality_findings(result.seasonality),
            result.seasonality.formula,
            result.seasonality.limitations,
        ),
        "cancellations": _analysis(
            cancellations_findings(result.cancellations),
            result.cancellations.formula,
            result.cancellations.limitations,
        ),
        "room_value": room_value,
        "guest_mix": _analysis(
            guest_mix_findings(result.guest_mix),
            result.guest_mix.formula,
            result.guest_mix.limitations,
        ),
        "occupancy": _analysis(
            occupancy_findings(result.occupancy),
            result.occupancy.formula,
            result.occupancy.limitations,
        ),
        "occupancy_on_holidays": _analysis(
            occupancy_on_holidays_findings(result.occupancy_on_holidays),
            result.occupancy_on_holidays.formula,
            result.occupancy_on_holidays.limitations,
        ),
        "correlations": _analysis(
            correlations_findings(result.correlations),
            result.correlations.formula,
            result.correlations.limitations,
        ),
    }


def _data_quality(bookings: list[Booking], result: MarketAnalysis) -> JsonObject:
    booking_dates = [b.booking_date for b in bookings if b.booking_date is not None]
    arrivals = [b.arrival_date for b in bookings]
    return {
        "record_count": result.record_count,
        "earliest_booking_date": min(booking_dates).isoformat() if booking_dates else None,
        "latest_booking_date": max(booking_dates).isoformat() if booking_dates else None,
        "earliest_arrival_date": min(arrivals).isoformat(),
        "latest_arrival_date": max(arrivals).isoformat(),
        "duplicate_booking_id_count": len(bookings) - len({b.booking_id for b in bookings}),
        "missing_counts": dict(result.missing_counts),
        # The request is checked field by field before a run starts, so none is invalid here.
        "invalid_counts": dict.fromkeys(result.missing_counts, 0),
        "zero_price_count": result.room_value.zero_price_records,
    }


def _add_insights(analyses: dict[str, JsonObject], provider: InsightProvider) -> bool:
    """Add the insight to every analysis; True when some insight is unavailable."""
    any_unavailable = False
    for name, analysis in analyses.items():
        insight = provider.insight_for(name, analysis)
        analysis["insight"] = insight
        any_unavailable = any_unavailable or insight.get("status") != AVAILABLE
    return any_unavailable


def build_market_result(
    result: MarketAnalysis,
    bookings: list[Booking],
    calendar: HolidayCalendar,
    result_id: str,
    generated_at: datetime,
    insights: InsightProvider | None,
) -> JsonObject:
    """The result document. ``insights`` is None when no insight was asked for."""
    analyses = _analyses(result, calendar)
    notices: list[JsonObject] = []
    if any(a["status"] == UNAVAILABLE for a in analyses.values()):
        notices.append(
            {"code": ANALYSES_UNAVAILABLE, "message": "Some analyses have no data to read."}
        )
    insights_section: JsonObject = {"requested": insights is not None}
    if insights is not None:
        insights_section.update(insights.info())
        if _add_insights(analyses, insights):
            notices.append(
                {
                    "code": INSIGHTS_UNAVAILABLE,
                    "message": "The insight of some analyses is unavailable.",
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "result_id": result_id,
        "generated_at": generated_at.isoformat(),
        "status": "completed_with_warnings" if notices else "completed",
        "input": {
            "source": INPUT_SOURCE,
            "reference": INPUT_REFERENCE,
            "record_count": result.record_count,
            "content_sha256": content_sha256(bookings),
            "room_count": result.occupancy.room_count,
            "period": date_range_data(result.occupancy.period),
        },
        "data_quality": _data_quality(bookings, result),
        "analyses": analyses,
        "notices": notices,
        "insights": insights_section,
    }
