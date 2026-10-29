from decimal import Decimal

from app.domain.analyses.guest_mix import analyse_guest_mix
from tests.unit.booking_factory import make_booking


def _bookings() -> list:
    return [
        make_booking(
            is_canceled=True,
            adults=2,
            children=0,
            country="PRT",
            meal="BB",
            assigned_room_type="A",
            is_repeated_guest=False,
            required_car_parking_spaces=0,
            total_of_special_requests=1,
            stays_in_week_nights=2,
            price_per_night=Decimal("100"),
        ),
        make_booking(
            adults=2,
            children=1,
            babies=0,
            country="PRT",
            meal="BB",
            assigned_room_type="A",
            is_repeated_guest=True,
            required_car_parking_spaces=1,
            total_of_special_requests=0,
            stays_in_week_nights=4,
            price_per_night=Decimal("50"),
        ),
        make_booking(country="GBR", assigned_room_type="B", stays_in_week_nights=3),
    ]


def test_total_guests_are_ordered_by_value_and_leave_out_unknown() -> None:
    dist = analyse_guest_mix(_bookings()).total_guests
    assert [(g.figure.group, g.figure.numerator, g.figure.denominator) for g in dist.groups] == [
        ("2", 1, 2),
        ("3", 1, 2),
    ]
    assert (dist.records_used, dist.records_left_out) == (2, 1)


def test_country_group_has_mean_stay_cancellation_share_and_mean_price() -> None:
    portugal, britain = analyse_guest_mix(_bookings()).country.groups
    assert portugal.figure.group == "PRT"
    assert (portugal.figure.numerator, portugal.figure.denominator) == (2, 3)
    assert portugal.mean_length_of_stay.value == Decimal("3.0000")  # (2 + 4) / 2
    assert (portugal.cancellation_share.numerator, portugal.cancellation_share.denominator) == (
        1,
        2,
    )
    assert portugal.mean_price_per_night.value == Decimal("75.0000")  # (100 + 50) / 2
    assert britain.mean_price_per_night.value is None
    assert britain.mean_price_per_night.count == 0


def test_bookings_without_the_trait_are_left_out_of_that_distribution() -> None:
    meal = analyse_guest_mix(_bookings()).meal
    assert [(g.figure.group, g.figure.numerator) for g in meal.groups] == [("BB", 2)]
    assert (meal.records_used, meal.records_left_out) == (2, 1)


def test_repeated_guest_is_named_and_ordered_by_size_then_name() -> None:
    groups = analyse_guest_mix(_bookings()).is_repeated_guest.groups
    assert [g.figure.group for g in groups] == ["not_repeated", "repeated"]


def test_parking_and_special_requests_are_numeric_distributions() -> None:
    result = analyse_guest_mix(_bookings())
    assert [g.figure.group for g in result.required_car_parking_spaces.groups] == ["0", "1"]
    assert [g.figure.group for g in result.total_of_special_requests.groups] == ["0", "1"]


def test_room_type_is_ordered_by_size() -> None:
    groups = analyse_guest_mix(_bookings()).assigned_room_type.groups
    assert [(g.figure.group, g.figure.numerator) for g in groups] == [("A", 2), ("B", 1)]
    assert all(g.figure.small_sample for g in groups)
