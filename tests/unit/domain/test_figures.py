from decimal import Decimal

import pytest

from app.domain.figures import count_figures, make_figure, mean_of


@pytest.mark.parametrize(
    ("denominator", "small"), [(0, True), (29, True), (30, False), (31, False)]
)
def test_small_sample_is_set_below_30(denominator: int, small: bool) -> None:
    assert make_figure("g", 0, denominator).small_sample is small


def test_share_is_none_without_a_denominator() -> None:
    assert make_figure("g", 0, 0).share is None


def test_share_is_numerator_over_denominator() -> None:
    assert make_figure("g", 1, 4).share == 0.25


def test_mean_of_rounds_to_four_places_half_up() -> None:
    assert mean_of([Decimal("1"), Decimal("1"), Decimal("2")]).value == Decimal("1.3333")
    assert mean_of([Decimal("0.00005")]).value == Decimal("0.0001")


def test_mean_of_nothing_has_no_value_and_is_a_small_sample() -> None:
    result = mean_of([])
    assert (result.value, result.count, result.small_sample) == (None, 0, True)


def test_count_figures_leaves_out_items_without_a_key() -> None:
    figures = count_figures(["a", "b", "a", "x"], lambda s: None if s == "x" else s)
    assert [(f.group, f.numerator, f.denominator) for f in figures] == [("a", 2, 3), ("b", 1, 3)]


def test_count_figures_with_a_flag_counts_the_flagged_over_the_group() -> None:
    figures = count_figures([1, 2, 3, 4, 5], lambda n: "odd" if n % 2 else "even", lambda n: n > 2)
    assert [(f.group, f.numerator, f.denominator) for f in figures] == [
        ("odd", 2, 3),
        ("even", 1, 2),
    ]
