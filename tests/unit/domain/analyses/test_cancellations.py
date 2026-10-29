from datetime import date

from app.domain.analyses.cancellations import analyse_cancellations
from app.domain.figures import Figure
from tests.unit.booking_factory import make_booking


def _bookings() -> list:
    return [
        make_booking(
            is_canceled=True,
            lead_time=5,
            deposit_type="No Deposit",
            market_segment="Online",
            customer_type="Transient",
            arrival_date=date(2024, 1, 5),
            total_of_special_requests=0,
            booking_changes=0,
        ),
        make_booking(
            lead_time=40,
            deposit_type="No Deposit",
            market_segment="Online",
            customer_type="Transient",
            arrival_date=date(2024, 1, 20),
            total_of_special_requests=2,
            booking_changes=1,
        ),
        make_booking(
            is_canceled=True,
            lead_time=100,
            deposit_type="Non Refund",
            market_segment="Groups",
            customer_type="Contract",
            arrival_date=date(2024, 2, 1),
            total_of_special_requests=10,
            booking_changes=0,
        ),
        make_booking(
            market_segment="Online",
            arrival_date=date(2024, 2, 10),
            total_of_special_requests=1,
        ),
    ]


def _shape(groups: tuple[Figure, ...]) -> list[tuple[str, int, int]]:
    return [(g.group, g.numerator, g.denominator) for g in groups]


def test_overall_share_is_cancelled_over_all_bookings() -> None:
    overall = analyse_cancellations(_bookings()).overall
    assert (overall.numerator, overall.denominator, overall.share) == (2, 4, 0.5)


def test_split_by_lead_time_band_leaves_out_bookings_without_lead_time() -> None:
    split = analyse_cancellations(_bookings()).by_lead_time_band
    assert _shape(split.groups) == [("0-7", 1, 1), ("31-90", 0, 1), ("91+", 1, 1)]
    assert (split.records_used, split.records_left_out) == (3, 1)


def test_split_by_deposit_type_is_ordered_by_group_size() -> None:
    split = analyse_cancellations(_bookings()).by_deposit_type
    assert _shape(split.groups) == [("No Deposit", 1, 2), ("Non Refund", 1, 1)]
    assert split.records_left_out == 1


def test_split_by_market_segment_and_customer_type() -> None:
    result = analyse_cancellations(_bookings())
    assert _shape(result.by_market_segment.groups) == [("Online", 1, 3), ("Groups", 1, 1)]
    assert _shape(result.by_customer_type.groups) == [("Transient", 1, 2), ("Contract", 1, 1)]


def test_split_by_arrival_month_is_chronological() -> None:
    split = analyse_cancellations(_bookings()).by_arrival_month
    assert _shape(split.groups) == [("2024-01", 1, 2), ("2024-02", 1, 2)]


def test_numeric_splits_are_ordered_by_value_not_by_text() -> None:
    result = analyse_cancellations(_bookings())
    assert _shape(result.by_special_requests.groups) == [
        ("0", 1, 1),
        ("1", 0, 1),
        ("2", 0, 1),
        ("10", 1, 1),
    ]
    assert _shape(result.by_booking_changes.groups) == [("0", 2, 2), ("1", 0, 1)]
    assert result.by_booking_changes.records_left_out == 1


def test_groups_below_30_bookings_are_small_samples() -> None:
    assert all(g.small_sample for g in analyse_cancellations(_bookings()).by_deposit_type.groups)
