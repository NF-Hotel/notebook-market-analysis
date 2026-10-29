import pytest

from app.domain.statistics import average_ranks, median, spearman


def test_median_of_odd_count_is_the_middle_value() -> None:
    assert median([9, 1, 5]) == 5.0


def test_median_of_even_count_is_the_mean_of_the_middle_values() -> None:
    assert median([4, 1, 3, 2]) == 2.5


def test_median_of_nothing_is_none() -> None:
    assert median([]) is None


def test_average_ranks_share_the_mean_rank_for_ties() -> None:
    assert average_ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_spearman_is_plus_one_for_series_that_move_together() -> None:
    assert spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) == 1.0


def test_spearman_is_minus_one_for_series_that_move_apart() -> None:
    assert spearman([1, 2, 3, 4, 5], [50, 40, 30, 20, 10]) == -1.0


def test_spearman_is_plus_one_for_a_steady_non_linear_rise() -> None:
    assert spearman([1, 2, 3], [1, 4, 100]) == 1.0


def test_spearman_with_ties_uses_average_ranks() -> None:
    # ranks x = 1,2,3,4; ranks y = 1,2.5,2.5,4; covariance 4.5; variances 5 and 4.5
    assert spearman([1, 2, 3, 4], [1, 2, 2, 3]) == pytest.approx(4.5 / 22.5**0.5)


@pytest.mark.parametrize(
    ("xs", "ys"),
    [([1, 1, 1], [1, 2, 3]), ([1, 2, 3], [5, 5, 5]), ([1], [2]), ([], [])],
)
def test_spearman_is_none_for_a_constant_series_or_fewer_than_two_pairs(
    xs: list[float], ys: list[float]
) -> None:
    assert spearman(xs, ys) is None


def test_spearman_rejects_series_of_different_length() -> None:
    with pytest.raises(ValueError, match="same length"):
        spearman([1, 2], [1])
