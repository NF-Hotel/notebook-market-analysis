from datetime import date
from decimal import Decimal

from app.domain.analyses.occupancy import analyse_occupancy
from app.domain.analyses.room_value import analyse_room_value
from app.domain.booking import Booking
from app.domain.forecast import Forecast, MeasureForecast, forecast_market
from app.domain.period import Period
from tests.unit.booking_factory import make_booking

PRICE = Decimal("100")


def _month_bookings(year: int, month: int, count: int, **changes: object) -> list[Booking]:
    """``count`` one-night bookings, one on each of the first days of the month, at 100 a night."""
    return [
        make_booking(
            booking_id=year * 10000 + month * 100 + day,
            arrival_date=date(year, month, day),
            price_per_night=PRICE,
            **changes,
        )
        for day in range(1, count + 1)
    ]


def _forecast(bookings: list[Booking], period: Period, room_count: int = 1) -> Forecast:
    occupancy = analyse_occupancy(bookings, room_count, period)
    return forecast_market(bookings, occupancy, analyse_room_value(bookings))


def _measure(forecast: Forecast, name: str) -> MeasureForecast:
    return next(m for m in forecast.measures if m.measure == name)


def _two_years() -> tuple[list[Booking], Period]:
    """Month m of 2023 has m bookings and month m of 2024 has 2m."""
    bookings = [
        b
        for year, factor in ((2023, 1), (2024, 2))
        for month in range(1, 13)
        for b in _month_bookings(year, month, month * factor)
    ]
    return bookings, Period(date(2023, 1, 1), date(2024, 12, 31))


def _points(forecast: Forecast, name: str) -> list[tuple[str, str, str | None, str | None]]:
    return [
        (p.month, str(p.expected), None if p.low is None else str(p.low), str(p.high))
        for p in _measure(forecast, name).points
    ]


def test_two_years_of_history_give_six_months_from_the_seasonal_mean() -> None:
    forecast = _forecast(*_two_years())
    assert forecast.history_months == 24
    assert forecast.history_too_short is False
    assert forecast.horizon_months == 6
    # Month m was seen m and 2m times: mean 1.5m, sample standard deviation m * sqrt(0.5).
    # January: 1.5 -/+ 0.7071 = 0.7929 .. 2.2071; June: 9 -/+ 4.2426 = 4.7574 .. 13.2426.
    arrivals = _measure(forecast, "arrivals")
    assert arrivals.unit == "bookings"
    assert [(p.month, p.expected, p.low, p.high) for p in arrivals.points] == [
        ("2025-01", Decimal("1.50"), Decimal("0.79"), Decimal("2.21")),
        ("2025-02", Decimal("3.00"), Decimal("1.59"), Decimal("4.41")),
        ("2025-03", Decimal("4.50"), Decimal("2.38"), Decimal("6.62")),
        ("2025-04", Decimal("6.00"), Decimal("3.17"), Decimal("8.83")),
        ("2025-05", Decimal("7.50"), Decimal("3.96"), Decimal("11.04")),
        ("2025-06", Decimal("9.00"), Decimal("4.76"), Decimal("13.24")),
    ]


def test_room_revenue_is_forecast_from_the_monthly_revenue() -> None:
    # Every booking is one night at 100, so the revenue of a month is 100 times its bookings.
    revenue = _measure(_forecast(*_two_years()), "room_revenue")
    assert revenue.unit == "price units"
    first, second = revenue.points[:2]
    assert (first.expected, first.low, first.high) == (
        Decimal("150.00"),
        Decimal("79.29"),
        Decimal("220.71"),
    )
    assert (second.expected, second.low, second.high) == (
        Decimal("300.00"),
        Decimal("158.58"),
        Decimal("441.42"),
    )


def test_occupancy_is_forecast_in_percent_of_the_room_nights() -> None:
    # One room: January held 1 of 31 nights in 2023 and 2 of 31 in 2024 (3.2258 % and 6.4516 %).
    # Mean 4.8387 %, standard deviation 3.2258 / sqrt(2) = 2.2810.
    occupancy = _measure(_forecast(*_two_years()), "occupancy")
    assert occupancy.unit == "%"
    january = occupancy.points[0]
    assert (january.month, january.expected) == ("2025-01", Decimal("4.84"))
    assert (january.low, january.high) == (Decimal("2.56"), Decimal("7.12"))


def test_cancelled_bookings_are_not_arrivals_or_revenue() -> None:
    bookings, period = _two_years()
    bookings += _month_bookings(2024, 1, 20, is_canceled=True)
    january = _measure(_forecast(bookings, period), "arrivals").points[0]
    assert january.expected == Decimal("1.50")
    january_revenue = _measure(_forecast(bookings, period), "room_revenue").points[0]
    assert january_revenue.expected == Decimal("150.00")


def test_a_history_below_24_months_is_flagged_and_below_12_months_gives_three_months() -> None:
    bookings = [b for m, n in ((1, 1), (2, 2), (3, 3)) for b in _month_bookings(2024, m, n)]
    forecast = _forecast(bookings, Period(date(2024, 1, 1), date(2024, 3, 31)))
    assert forecast.history_months == 3
    assert forecast.minimum_history_months == 24
    assert forecast.history_too_short is True
    assert forecast.horizon_months == 3
    # No calendar month is seen twice: the mean of all three months, 2, with the standard
    # deviation of 1, 2 and 3 (1.0).
    assert _points(forecast, "arrivals") == [
        ("2024-04", "2.00", "1.00", "3.00"),
        ("2024-05", "2.00", "1.00", "3.00"),
        ("2024-06", "2.00", "1.00", "3.00"),
    ]


def test_a_year_of_history_gives_six_months_and_is_still_too_short() -> None:
    bookings = [b for m in range(1, 13) for b in _month_bookings(2024, m, m)]
    forecast = _forecast(bookings, Period(date(2024, 1, 1), date(2024, 12, 31)))
    assert (forecast.history_months, forecast.horizon_months) == (12, 6)
    assert forecast.history_too_short is True
    # Each calendar month was seen once: the value of that month, the spread of all twelve
    # (the sample standard deviation of 1..12 is 3.6056).
    january = _measure(forecast, "arrivals").points[0]
    assert (january.month, january.expected) == ("2025-01", Decimal("1.00"))
    assert (january.low, january.high) == (Decimal("0.00"), Decimal("4.61"))


def test_a_partial_first_and_last_month_are_not_in_the_history() -> None:
    bookings = [b for m in (1, 2, 3, 4) for b in _month_bookings(2024, m, 2)]
    forecast = _forecast(bookings, Period(date(2024, 1, 15), date(2024, 4, 20)))
    assert forecast.history_months == 2  # February and March
    assert _measure(forecast, "arrivals").points[0].month == "2024-04"


def test_a_single_month_has_no_band() -> None:
    bookings = _month_bookings(2024, 2, 4)
    forecast = _forecast(bookings, Period(date(2024, 2, 1), date(2024, 2, 29)))
    point = _measure(forecast, "arrivals").points[0]
    assert (point.expected, point.low, point.high) == (Decimal("4.00"), None, None)


def test_without_a_complete_month_there_is_no_forecast() -> None:
    bookings = _month_bookings(2024, 2, 4)
    forecast = _forecast(bookings, Period(date(2024, 2, 1), date(2024, 2, 20)))
    assert (forecast.history_months, forecast.horizon_months) == (0, 0)
    assert forecast.history_too_short is True
    assert all(m.points == () for m in forecast.measures)
