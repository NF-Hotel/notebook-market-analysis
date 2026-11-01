import pytest

from app.application.chart_series import ChartSeries, SeriesPoint
from app.application.insight_guardrail import (
    FORBIDDEN_PHRASES,
    FORECAST_PHRASES,
    evidence_is_in_series,
    makes_forbidden_claim,
    names_a_number,
    names_only_numbers_of,
)


def _series(unit: str = "%") -> ChartSeries:
    points = (
        SeriesPoint("No Deposit", 24.7, 9450, 38199),
        SeriesPoint("Refundable", 15.5, 22, 142),
        SeriesPoint("2019-07", 22.0, 11, 50),
    )
    return ChartSeries("splits.by_deposit_type.groups", "By deposit type", unit, points)


@pytest.mark.parametrize(
    "text",
    [
        "Bookings will increase next season.",
        "Cancellations are high BECAUSE of the price.",
        "This is caused by the lead time.",
        "We guarantee fewer cancellations.",
        "The forecast is positive.",
        "Demand is predicted to rise.",
    ],
)
def test_a_causal_or_forecast_phrase_is_a_forbidden_claim(text: str) -> None:
    assert makes_forbidden_claim(text)


@pytest.mark.parametrize(
    "text",
    [
        "Cancellations are higher in the group with no deposit.",
        "The share is 24.7 for no deposit and 15.5 for refundable.",
        "The causeway is long.",
    ],
)
def test_a_description_of_an_association_is_not_a_forbidden_claim(text: str) -> None:
    assert not makes_forbidden_claim(text)


def test_every_forbidden_phrase_is_found() -> None:
    assert all(makes_forbidden_claim(f"The data {p} it.") for p in FORBIDDEN_PHRASES)


def test_a_word_of_a_phrase_inside_another_word_is_not_found() -> None:
    assert not makes_forbidden_claim("The unforecastable is not here.")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("No numbers here.", False), ("It is 24.7.", True), ("Q3 only", False), ("55,484 rows", True)],
)
def test_names_a_number(text: str, expected: bool) -> None:
    assert names_a_number(text) is expected


@pytest.mark.parametrize(
    "evidence",
    [
        "24.7",
        "24.7%",
        "No Deposit is 24.7 and Refundable is 15.5",
        "about 25",  # 24.7 rounded to no decimal
        "24.70",  # 24.7 rounded to two decimals
        "0.247",  # a share written as a fraction
        "9,450 of 38,199",  # numerator and denominator are figures of the series
        "22 of 142 bookings",
        "2019-07 is 22.0",  # the digits of a label are not figures
    ],
)
def test_evidence_with_numbers_of_the_series_is_in_the_series(evidence: str) -> None:
    assert evidence_is_in_series(evidence, _series())


@pytest.mark.parametrize(
    "evidence",
    [
        "no numbers at all",
        "24.8",  # one tenth off
        "24.7 and 31.2",  # one number is not in the series
        "0.26",  # a fraction does not round to 24.7
        "0.247%",  # a percent sign means percent, not a fraction
        "1",  # a stray digit is not a share as fraction
        "24.7 in 2019",
    ],
)
def test_evidence_with_a_number_that_is_not_in_the_series_is_not_accepted(evidence: str) -> None:
    assert not evidence_is_in_series(evidence, _series())


def test_a_fraction_is_accepted_only_for_a_percent_series() -> None:
    assert not evidence_is_in_series("0.247", _series(unit="bookings"))


def _forecast_series() -> ChartSeries:
    points = (
        SeriesPoint("2025-01", 150.0, low=79.29, high=220.71),
        SeriesPoint("2025-02", 300.0, low=158.58, high=441.42),
    )
    return ChartSeries(
        "forecast.arrivals", "Forecast of arrivals", "bookings", points, (30.0, 24.0)
    )


@pytest.mark.parametrize(
    "text",
    ["The forecast is 150.", "The projected value is 150.", "Next month is 150."],
)
def test_the_words_that_describe_the_forecast_of_the_service_are_allowed_only_on_its_chart(
    text: str,
) -> None:
    assert makes_forbidden_claim(text)
    assert not makes_forbidden_claim(text, is_forecast_chart=True)


@pytest.mark.parametrize(
    "text",
    [
        "Arrivals will increase.",
        "This is due to the season.",
        "We guarantee 150.",
        "Arrivals are expected to rise next year.",
        "We predict 150.",
    ],
)
def test_promises_causes_and_own_predictions_are_forbidden_on_the_forecast_chart_too(
    text: str,
) -> None:
    assert makes_forbidden_claim(text, is_forecast_chart=True)


def test_the_forecast_phrases_are_forbidden_phrases() -> None:
    assert set(FORECAST_PHRASES) <= set(FORBIDDEN_PHRASES)


def test_the_band_and_the_months_of_history_of_a_forecast_are_figures_of_its_series() -> None:
    series = _forecast_series()
    assert evidence_is_in_series("150.00, 79.29, 220.71 and 30 months", series)
    assert not evidence_is_in_series("150.00 and 999", series)


def test_a_text_may_write_no_number_but_not_a_number_that_is_not_in_the_series() -> None:
    assert names_only_numbers_of("The first group is higher.", _series())
    assert names_only_numbers_of("No Deposit is 24.7 of 38199.", _series())
    assert not names_only_numbers_of("No Deposit is 31.4.", _series())


def _monthly_series() -> ChartSeries:
    points = tuple(
        SeriesPoint(f"2025-{month:02d}", value, num, 156686.0)
        for month, value, num in ((4, 1.3, 2037.0), (7, 0.6, 940.0))
    )
    return ChartSeries("monthly", "Arrivals (latest 30 of 102 months)", "%", points)


@pytest.mark.parametrize(
    "evidence",
    [
        "April 2026: 1.3%, July 2025: 0.6%, Denominator: 156,686 records.",
        "from July 2024 to December 2026, 1.3%",
        "Jul 2025 at 0.6%",
        "the latest 30 of 102 months, 1.3%",
        "30 months, 2 points, 1.3%",
    ],
)
def test_a_year_after_a_month_name_and_the_counts_of_the_title_are_not_checked(
    evidence: str,
) -> None:
    assert evidence_is_in_series(evidence, _monthly_series())


@pytest.mark.parametrize(
    "text",
    [
        "April 2026 at 1.4%",  # a made-up figure next to a year
        "In 2026 it was 1.3% and 99 elsewhere",
        "1.3% in 2026",  # a year with no month name
        "April 2026 and 2027 at 1.3%",  # only the year right after the month is a date
        "April 12345 at 1.3%",
        "may 2026 at 1.3%",  # the verb "may" is not a month name
    ],
)
def test_a_number_beside_a_year_or_a_year_that_is_not_after_a_month_is_still_checked(
    text: str,
) -> None:
    assert not evidence_is_in_series(text, _monthly_series())
    assert not names_only_numbers_of(text, _monthly_series())


def test_the_counts_of_a_title_are_figures_only_when_the_title_has_them() -> None:
    plain = ChartSeries("c", "Arrivals", "%", _monthly_series().points)
    assert not names_only_numbers_of("It is 102.", plain)
    assert names_only_numbers_of("It is 102.", _monthly_series())
