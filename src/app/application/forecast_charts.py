"""The forecast of the service as charts for the model: one chart for each analysis it belongs to.

The forecast is calculated in the domain layer. The model may comment on its figures; it never
makes a forecast of its own.
"""

from __future__ import annotations

from app.application.chart_series import ChartSeries, SeriesPoint
from app.application.documents import JsonObject
from app.domain.forecast import MEASURE_ARRIVALS, MEASURE_OCCUPANCY, MEASURE_ROOM_REVENUE

FORECAST_KEY = "forecast"
FORECAST_SERIES_PREFIX = "forecast."
# The analysis that a forecast measure is shown with.
MEASURE_OF_ANALYSIS: dict[str, str] = {
    "seasonality": MEASURE_ARRIVALS,
    "occupancy": MEASURE_OCCUPANCY,
    "room_value": MEASURE_ROOM_REVENUE,
}
_MEASURE_TITLES = {
    MEASURE_ARRIVALS: "Forecast of arrivals",
    MEASURE_OCCUPANCY: "Forecast of occupancy",
    MEASURE_ROOM_REVENUE: "Forecast of room revenue",
}


def forecast_for_analysis(name: str, forecast: JsonObject) -> JsonObject | None:
    """The part of the forecast that belongs to the analysis ``name``, or None."""
    measure = MEASURE_OF_ANALYSIS.get(name)
    if measure is None:
        return None
    data = forecast["measures"][measure]
    return {
        "measure": measure,
        "unit": data["unit"],
        "history_months": forecast["history_months"],
        "history_too_short": forecast["history_too_short"],
        "minimum_history_months": forecast["minimum_history_months"],
        "months": data["months"],
    }


def _number(value: str | None) -> float | None:
    return None if value is None else float(value)


def forecast_chart(forecast: JsonObject) -> ChartSeries | None:
    """The chart of a forecast part (see ``forecast_for_analysis``); None without months."""
    months = forecast.get("months") or []
    if not months:
        return None
    measure = str(forecast["measure"])
    points = tuple(
        SeriesPoint(m["group"], float(m["value"]), low=_number(m["low"]), high=_number(m["high"]))
        for m in months
    )
    facts = (float(forecast["history_months"]), float(forecast["minimum_history_months"]))
    return ChartSeries(
        f"{FORECAST_SERIES_PREFIX}{measure}",
        _MEASURE_TITLES[measure],
        str(forecast["unit"]),
        points,
        facts=facts,
        is_forecast=True,
    )
