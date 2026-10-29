from decimal import Decimal

import pytest

from app.domain.analyses.correlations import FIELDS, analyse_correlations
from app.domain.booking import Booking
from tests.unit.booking_factory import make_booking


def _cell(matrix: tuple[tuple[float | None, ...], ...], row: str, column: str) -> float | None:
    return matrix[FIELDS.index(row)][FIELDS.index(column)]


def _series(
    leads: list[int | None], prices: list[str], canceled: list[bool] | None = None
) -> list[Booking]:
    flags = canceled or [False] * len(leads)
    return [
        make_booking(lead_time=lead, price_per_night=Decimal(price), is_canceled=flag)
        for lead, price, flag in zip(leads, prices, flags, strict=True)
    ]


def test_fields_are_the_numeric_booking_fields_and_is_canceled() -> None:
    result = analyse_correlations([make_booking()])
    assert result.method == "spearman"
    assert result.fields[-1] == "is_canceled"
    assert "lead_time" in result.fields
    assert len(result.matrix) == len(result.fields)
    assert all(len(row) == len(result.fields) for row in result.matrix)


def test_series_built_to_move_together_give_plus_one() -> None:
    result = analyse_correlations(_series([1, 2, 3, 4, 5], ["10", "20", "30", "40", "50"]))
    assert _cell(result.matrix, "lead_time", "price_per_night") == 1.0


def test_series_built_to_move_apart_give_minus_one() -> None:
    result = analyse_correlations(_series([1, 2, 3, 4, 5], ["50", "40", "30", "20", "10"]))
    assert _cell(result.matrix, "lead_time", "price_per_night") == -1.0
    assert _cell(result.matrix, "price_per_night", "lead_time") == -1.0


def test_correlation_with_cancelled_uses_average_ranks_for_the_tie() -> None:
    # lead 10..40 against cancelled F, F, T, T: ranks 1..4 against 1.5, 1.5, 3.5, 3.5;
    # covariance 4, variances 5 and 4: 4 / sqrt(20)
    result = analyse_correlations(
        _series([10, 20, 30, 40], ["1", "1", "1", "1"], [False, False, True, True])
    )
    assert _cell(result.matrix, "lead_time", "is_canceled") == pytest.approx(4 / 20**0.5)
    assert _cell(result.matrix, "is_canceled", "lead_time") == pytest.approx(4 / 20**0.5)


def test_a_field_with_a_value_of_every_booking_correlates_one_with_itself() -> None:
    result = analyse_correlations(_series([1, 2, 3], ["5", "6", "7"]))
    assert _cell(result.matrix, "lead_time", "lead_time") == 1.0


def test_a_constant_or_wholly_missing_field_gives_none_and_no_crash() -> None:
    result = analyse_correlations(_series([1, 2, 3], ["5", "6", "7"]))
    # stays_in_week_nights is 1 for every booking, children is missing for every booking
    assert _cell(result.matrix, "stays_in_week_nights", "lead_time") is None
    assert _cell(result.matrix, "children", "lead_time") is None
    assert _cell(result.matrix, "children", "children") is None
    assert result.records_used[FIELDS.index("children")] == 0


def test_missing_values_are_left_out_of_the_pair_and_counted() -> None:
    # The fifth booking has no lead time; the other four rise together with the price.
    result = analyse_correlations(_series([1, 2, 3, 4, None], ["10", "20", "30", "40", "5"]))
    assert _cell(result.matrix, "lead_time", "price_per_night") == 1.0
    assert result.records_used[FIELDS.index("lead_time")] == 4
    assert result.records_used[FIELDS.index("price_per_night")] == 5


def test_fewer_than_two_records_give_none() -> None:
    result = analyse_correlations(_series([1], ["10"]))
    assert _cell(result.matrix, "lead_time", "price_per_night") is None


def test_no_bookings_give_a_matrix_of_none() -> None:
    result = analyse_correlations([])
    assert all(value is None for row in result.matrix for value in row)


def test_every_value_is_between_minus_one_and_one_or_none() -> None:
    result = analyse_correlations(
        _series([3, 1, 2, 5, 4], ["7", "7", "9", "1", "4"], [True, False] * 2 + [True])
    )
    for row in result.matrix:
        for value in row:
            assert value is None or -1.0 <= value <= 1.0
