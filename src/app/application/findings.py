"""The findings of each analysis as plain data in the shape of result schema 1.1.

The free text (``summary``, ``statement``, ``note``) is short, factual English built from the
figures; it makes no claim the figures do not hold.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import Decimal

from app.application.documents import JsonObject
from app.domain.analyses.cancellations import CancellationAnalysis, CancellationSplit
from app.domain.analyses.correlations import CorrelationsAnalysis
from app.domain.analyses.guest_mix import Distribution, GuestGroup, GuestMixAnalysis
from app.domain.analyses.holiday_effect import (
    DayGroup,
    HolidayAnalysis,
    HolidayComparison,
    HolidayMeasure,
)
from app.domain.analyses.lead_time import LeadTimeAnalysis, LeadTimeGroup
from app.domain.analyses.occupancy import OccupancyAnalysis
from app.domain.analyses.occupancy_on_holidays import OccupancyOnHolidaysAnalysis
from app.domain.analyses.room_value import EstimatedValueGroup, RoomValueAnalysis
from app.domain.analyses.seasonality import (
    PeriodFigure,
    SeasonalityAnalysis,
    SeasonalityMeasure,
)
from app.domain.figures import Figure, MeanValue
from app.domain.holidays import HolidayCalendar
from app.domain.period import Period

AVAILABLE = "available"
UNAVAILABLE = "unavailable"
OBSERVED_ONLY = "this is an observed association only."


def figure_data(figure: Figure) -> JsonObject:
    return {
        "group": figure.group,
        "numerator": figure.numerator,
        "denominator": figure.denominator,
        "small_sample": figure.small_sample,
    }


def date_range_data(period: Period) -> JsonObject:
    return {"first_date": period.first_date.isoformat(), "last_date": period.last_date.isoformat()}


def _span_data(period: Period | None) -> JsonObject | None:
    if period is None:
        return None
    return {"first": period.first_date.isoformat(), "last": period.last_date.isoformat()}


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _mean_data(mean: MeanValue) -> JsonObject:
    return {
        "value": _decimal_text(mean.value),
        "count": mean.count,
        "small_sample": mean.small_sample,
    }


def _status(has_data: bool) -> str:
    return AVAILABLE if has_data else UNAVAILABLE


def _percent(figure: Figure) -> str:
    share = figure.share
    return "not known" if share is None else f"{share * 100:.1f} %"


def _label(name: str) -> str:
    return name.removeprefix("by_").replace("_", " ")


def _period_text(period: Period) -> str:
    return f"from {period.first_date.isoformat()} to {period.last_date.isoformat()}"


# --- lead time ---------------------------------------------------------------------------


def _median_summary(group: LeadTimeGroup) -> str:
    if group.median_days is None:
        return "No lead time is known for this group."
    return (
        f"The median lead time was {group.median_days:g} days across "
        f"{group.figure.numerator} records; this describes the observed distribution."
    )


def _lead_group_data(group: LeadTimeGroup) -> JsonObject:
    return {
        "figure": figure_data(group.figure),
        "median_days": group.median_days,
        "bands": [figure_data(b) for b in group.bands],
        "summary": _median_summary(group),
    }


def _lead_split_data(groups: Sequence[LeadTimeGroup]) -> JsonObject:
    return {"status": _status(bool(groups)), "groups": [_lead_group_data(g) for g in groups]}


def lead_time_findings(analysis: LeadTimeAnalysis) -> JsonObject:
    return {
        "unit": analysis.unit,
        "records_used": analysis.records_used,
        "records_without_lead_time": analysis.records_without_lead_time,
        "overall": _lead_group_data(analysis.overall),
        "splits": {
            "by_cancellation_status": _lead_split_data(analysis.by_cancellation_status),
            "by_arrival_month": _lead_split_data(analysis.by_arrival_month),
            "by_market_segment": _lead_split_data(analysis.by_market_segment),
            "by_customer_type": _lead_split_data(analysis.by_customer_type),
        },
    }


# --- holidays ----------------------------------------------------------------------------

HOLIDAYS_NOTE = (
    "Holiday figures describe associations between dates and activity; other factors are not "
    "adjusted for. Days in years the holiday calendar does not cover are left out."
)


def _day_group_data(group: DayGroup) -> JsonObject:
    data: JsonObject = {"figure": figure_data(group.figure), "mean_per_day": group.mean_per_day}
    if group.cancellation is not None:
        data["cancellation_share"] = figure_data(group.cancellation)
    return data


def _where(comparison: HolidayComparison) -> str:
    if comparison.window_days is None:
        return "on holidays"
    return f"in the {comparison.window_days}-day window {comparison.day_kind} holidays"


def _comparison_statement(noun: str, comparison: HolidayComparison) -> str:
    group = comparison.group.mean_per_day
    baseline = comparison.baseline.mean_per_day
    if group is None or baseline is None:
        return f"No comparison of {noun} per day can be stated; one of the groups has no days."
    where = _where(comparison)
    tail = f"({baseline:.2f}); {OBSERVED_ONLY}"
    if group == baseline:
        return f"Mean {noun} per day was the same {where} ({group:.2f}) as on baseline days {tail}"
    direction = "higher" if group > baseline else "lower"
    return (
        f"Mean {noun} per day was {direction} {where} ({group:.2f}) than on baseline days of "
        f"the same weekdays {tail}"
    )


def _comparison_data(noun: str, comparison: HolidayComparison) -> JsonObject:
    return {
        "day_kind": comparison.day_kind,
        "window_days": comparison.window_days,
        "group": _day_group_data(comparison.group),
        "baseline_same_weekdays": _day_group_data(comparison.baseline),
        "statement": _comparison_statement(noun, comparison),
    }


def _holiday_measure_data(measure: HolidayMeasure) -> JsonObject:
    noun = measure.measure
    return {
        "status": _status(measure.span is not None),
        "measure": noun,
        "date_field": measure.date_field,
        "span": _span_data(measure.span),
        "years_unavailable": list(measure.years_unavailable),
        "records_used": measure.records_used,
        "records_missing_date": measure.records_missing_date,
        "records_left_out_unavailable_years": measure.records_left_out_unavailable_years,
        "holiday_days": (
            None if measure.holiday is None else _comparison_data(noun, measure.holiday)
        ),
        "windows": [_comparison_data(noun, w) for w in measure.windows],
    }


def holidays_findings(analysis: HolidayAnalysis, calendar: HolidayCalendar) -> JsonObject:
    return {
        "calendar": f"{calendar.source}, country {calendar.country}",
        "windows_days": list(analysis.windows_days),
        "note": HOLIDAYS_NOTE,
        "booking_date": _holiday_measure_data(analysis.booking_date),
        "arrival_date": _holiday_measure_data(analysis.arrival_date),
    }


# --- seasonality -------------------------------------------------------------------------

SEASONALITY_NOTE = (
    "Bookings are counted by booking date and arrivals by arrival date, as separate series. "
    "Figures describe observed counts per period; no seasons are defined, and a partial period "
    "is not fully covered by the observed dates."
)


def _period_figure_data(period: PeriodFigure) -> JsonObject:
    return {
        "figure": figure_data(period.figure),
        "partial_period": period.partial_period,
        "cancellation": figure_data(period.cancellation),
        "mean_price_per_night": _mean_data(period.mean_price_per_night),
    }


def _seasonality_summary(measure: SeasonalityMeasure) -> str:
    if measure.span is None:
        return f"No {measure.measure} have a {measure.date_field}."
    partial = sum(p.partial_period for p in (*measure.monthly, *measure.iso_week))
    return (
        f"{measure.records_used} {measure.measure} were observed {_period_text(measure.span)}, "
        f"in {len(measure.monthly)} months and {len(measure.iso_week)} ISO weeks; {partial} of "
        "these periods are partial. This describes the observed data only."
    )


def _seasonality_measure_data(measure: SeasonalityMeasure) -> JsonObject:
    return {
        "status": _status(measure.span is not None),
        "measure": measure.measure,
        "date_field": measure.date_field,
        "span": _span_data(measure.span),
        "records_used": measure.records_used,
        "records_missing_date": measure.records_missing_date,
        "summary": _seasonality_summary(measure),
        "monthly": {"periods": [_period_figure_data(p) for p in measure.monthly]},
        "iso_week": {"periods": [_period_figure_data(p) for p in measure.iso_week]},
        "incomplete_years": [
            {"year": y.year, "months_present": y.months_present} for y in measure.incomplete_years
        ],
    }


def seasonality_findings(analysis: SeasonalityAnalysis) -> JsonObject:
    return {
        "note": SEASONALITY_NOTE,
        "bookings": _seasonality_measure_data(analysis.bookings),
        "arrivals": _seasonality_measure_data(analysis.arrivals),
    }


# --- cancellations -----------------------------------------------------------------------

CANCELLATIONS_NOTE = (
    "Cancellation shares are observed associations between a booking attribute and "
    "cancellation status; other factors are not adjusted for, and nothing is predicted."
)
CANCELLATION_SPLITS: tuple[str, ...] = (
    "by_lead_time_band",
    "by_deposit_type",
    "by_market_segment",
    "by_customer_type",
    "by_arrival_month",
    "by_special_requests",
    "by_booking_changes",
)


def _cancellation_split_data(name: str, split: CancellationSplit, overall: Figure) -> JsonObject:
    return {
        "status": _status(bool(split.groups)),
        "records_used": split.records_used,
        "records_left_out": split.records_left_out,
        "groups": [{"figure": figure_data(g)} for g in split.groups],
        "summary": (
            f"Cancellation share by {_label(name)}: {overall.numerator} of "
            f"{overall.denominator} bookings were cancelled overall; groups are shown with "
            "their counts and small groups are flagged."
        ),
    }


def cancellations_findings(analysis: CancellationAnalysis) -> JsonObject:
    return {
        "note": CANCELLATIONS_NOTE,
        "records_used": analysis.records_used,
        "overall": figure_data(analysis.overall),
        "splits": {
            name: _cancellation_split_data(name, getattr(analysis, name), analysis.overall)
            for name in CANCELLATION_SPLITS
        },
    }


# --- room value --------------------------------------------------------------------------

ESTIMATE_UNIT = "price units of the input"


def _value_summary(group: EstimatedValueGroup) -> str:
    mean = _decimal_text(group.value_per_booking.value)
    mean_text = "no mean (no booking has a price)" if mean is None else f"mean {mean}"
    return (
        f"Estimated value of {group.figure.numerator} bookings in group "
        f"'{group.figure.group}': total {_decimal_text(group.total)}, {mean_text} in the "
        "price units of the input (an estimate, not realized revenue)."
    )


def _value_group_data(group: EstimatedValueGroup) -> JsonObject:
    return {
        "figure": figure_data(group.figure),
        "total": _decimal_text(group.total),
        "mean": _decimal_text(group.value_per_booking.value),
        "records_with_price": group.value_per_booking.count,
        "records_without_price": group.records_without_price,
        "zero_price_records": group.zero_price_records,
        "summary": _value_summary(group),
    }


def room_value_findings(analysis: RoomValueAnalysis) -> JsonObject:
    return {
        "estimate": {
            "notice_code": analysis.estimate_notice_code,
            "label": analysis.estimate_label,
            "unit": ESTIMATE_UNIT,
        },
        "records_used": analysis.records_used,
        "zero_night_records": analysis.zero_night_records,
        "length_of_stay": {
            "unit": "nights",
            "records_used": analysis.records_used,
            "total_nights": analysis.total_nights,
            "buckets": [figure_data(f) for f in analysis.length_of_stay],
        },
        "estimated_value": {
            "status": _status(analysis.overall.value_per_booking.count > 0),
            "unit": ESTIMATE_UNIT,
            "label": analysis.estimate_label,
            "records_used": analysis.records_used,
            "records_without_price": analysis.records_without_price,
            "zero_price_records": analysis.zero_price_records,
            "overall": _value_group_data(analysis.overall),
            "groups": [_value_group_data(g) for g in analysis.by_cancellation_status],
        },
    }


# --- guest mix ---------------------------------------------------------------------------

GUEST_MIX_NOTE = (
    "Distributions show how bookings are spread over each attribute. A comparison is stated "
    "only for groups that are not small samples; it describes an observed association only."
)
DISTRIBUTIONS: tuple[str, ...] = (
    "total_guests",
    "country",
    "meal",
    "assigned_room_type",
    "is_repeated_guest",
    "required_car_parking_spaces",
    "total_of_special_requests",
)


def _comparison_of(group: GuestGroup) -> JsonObject:
    figure = group.figure
    if figure.small_sample:
        return {
            "status": "omitted_small_sample",
            "statement": (
                f"No comparison is stated for group '{figure.group}'; it is a small sample of "
                f"{figure.numerator} records."
            ),
        }
    return {
        "status": AVAILABLE,
        "mean_length_of_stay": _mean_data(group.mean_length_of_stay),
        "cancellation_share": figure_data(group.cancellation_share),
        "mean_price_per_night": _mean_data(group.mean_price_per_night),
    }


def _distribution_data(distribution: Distribution) -> JsonObject:
    return {
        "status": _status(bool(distribution.groups)),
        "records_used": distribution.records_used,
        "records_left_out": distribution.records_left_out,
        "groups": [
            {"figure": figure_data(g.figure), "comparison": _comparison_of(g)}
            for g in distribution.groups
        ],
    }


def guest_mix_findings(analysis: GuestMixAnalysis) -> JsonObject:
    return {
        "note": GUEST_MIX_NOTE,
        "distributions": {
            name: _distribution_data(getattr(analysis, name)) for name in DISTRIBUTIONS
        },
    }


# --- occupancy, occupancy on holidays, correlations --------------------------------------


def occupancy_findings(analysis: OccupancyAnalysis) -> JsonObject:
    overall = analysis.overall
    return {
        "room_count": analysis.room_count,
        "period": date_range_data(analysis.period),
        "overall": figure_data(overall),
        "monthly": [figure_data(f) for f in analysis.monthly],
        "over_capacity_days": analysis.over_capacity_days,
        "summary": (
            f"Occupancy was {_percent(overall)} ({overall.numerator} of {overall.denominator} "
            f"room nights) {_period_text(analysis.period)}."
        ),
    }


def occupancy_on_holidays_findings(analysis: OccupancyOnHolidaysAnalysis) -> JsonObject:
    holiday, other = analysis.holiday_days, analysis.other_days
    return {
        "room_count": analysis.room_count,
        "period": date_range_data(analysis.period),
        "holiday_days": figure_data(holiday),
        "other_days": figure_data(other),
        "days_left_out_unavailable_years": analysis.days_left_out_unavailable_years,
        "summary": (
            f"Occupancy was {_percent(holiday)} on holiday days and {_percent(other)} on other "
            f"days {_period_text(analysis.period)}; {OBSERVED_ONLY}"
        ),
    }


def _bounded(value: float | None) -> float | None:
    """A correlation inside -1 and 1; rounding noise is clamped, NaN is unknown."""
    if value is None or math.isnan(value):
        return None
    return max(-1.0, min(1.0, value))


def correlations_findings(analysis: CorrelationsAnalysis) -> JsonObject:
    return {
        "method": analysis.method,
        "fields": list(analysis.fields),
        "matrix": [[_bounded(v) for v in row] for row in analysis.matrix],
        "records_used": list(analysis.records_used),
        "summary": (
            f"Spearman rank correlation between {len(analysis.fields)} fields, each pair over "
            "the bookings that have both values; a correlation is not a cause."
        ),
    }
