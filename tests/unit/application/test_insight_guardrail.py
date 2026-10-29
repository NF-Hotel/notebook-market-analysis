import pytest

from app.application.chart_series import ChartSeries, SeriesPoint
from app.application.insight_guardrail import (
    FORBIDDEN_PHRASES,
    evidence_is_in_series,
    makes_forbidden_claim,
    names_a_number,
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
