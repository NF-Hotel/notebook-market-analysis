import json
from pathlib import Path
from typing import Any

from app.application.chart_series import MAX_POINTS, MAX_SERIES, chart_series

SAMPLE = Path(__file__).parents[3] / "docs" / "test-data" / "market-analysis-result.json"


def _group(label: str, numerator: int = 1, denominator: int = 4) -> dict[str, Any]:
    return {"group": label, "numerator": numerator, "denominator": denominator}


def test_wrapped_figures_are_one_series_with_the_dotted_path_as_id() -> None:
    findings = {
        "splits": {
            "by_deposit_type": {
                "status": "available",
                "groups": [
                    {"figure": _group("No Deposit", 9450, 38199)},
                    {"figure": _group("Refundable", 22, 142), "partial_period": False},
                ],
            }
        }
    }
    (series,) = chart_series(findings)
    assert (series.id, series.title, series.unit) == (
        "splits.by_deposit_type.groups",
        "By deposit type",
        "%",
    )
    assert [p.label for p in series.points] == ["No Deposit", "Refundable"]
    assert series.points[0].value == 24.7
    assert (series.points[0].numerator, series.points[0].denominator) == (9450, 38199)


def test_value_string_and_count_are_read_as_figures() -> None:
    findings = {
        "a": [{"group": "x", "value": "12.50"}],
        "b": [{"group": 3, "count": 7}],
    }
    a, b = chart_series(findings)
    assert (a.id, a.points[0].value, a.unit) == ("a", 12.5, "")
    assert (b.id, b.points[0].label, b.points[0].value, b.unit) == ("b", "3", 7, "bookings")


def test_a_point_with_a_zero_denominator_is_left_out() -> None:
    findings = {"g": [_group("a", 1, 0), _group("b", 1, 2)]}
    (series,) = chart_series(findings)
    assert [p.label for p in series.points] == ["b"]


def test_two_figures_in_the_root_are_one_series_joined_by_plus() -> None:
    findings = {
        "room_count": 20,
        "holiday_days": _group("holiday", 50, 100),
        "other_days": _group("other", 25, 100),
    }
    (series,) = chart_series(findings)
    assert series.id == "holiday_days+other_days"
    assert series.title == "Holiday days and other days"
    assert [(p.label, p.value) for p in series.points] == [
        ("Holiday days", 50.0),
        ("Other days", 25.0),
    ]


def test_one_figure_in_the_root_is_no_chart() -> None:
    assert chart_series({"overall": _group("all")}) == []


def test_an_unavailable_part_is_not_drawn() -> None:
    findings = {"estimated": {"status": "unavailable", "groups": [_group("a")]}}
    assert chart_series(findings) == []


def test_findings_without_group_figures_give_no_chart() -> None:
    assert chart_series({"fields": ["a"], "matrix": [[1.0]]}) == []


def test_lists_of_items_are_found_under_their_index() -> None:
    findings = {"windows": [{"groups": [_group("a")]}, {"groups": [_group("b")]}]}
    assert [s.id for s in chart_series(findings)] == ["windows.0.groups", "windows.1.groups"]


def test_shallow_and_short_series_come_first() -> None:
    findings = {
        "deep": {"deeper": {"groups": [_group("a")]}},
        "mid": {"groups": [_group("a"), _group("b"), _group("c")]},
        "top": [_group("a"), _group("b")],
    }
    assert [s.id for s in chart_series(findings)] == ["top", "mid.groups", "deep.deeper.groups"]


def test_a_category_series_of_more_than_30_points_keeps_the_first_30() -> None:
    findings = {"groups": [_group(f"c{i}") for i in range(45)]}
    (series,) = chart_series(findings)
    assert len(series.points) == MAX_POINTS
    assert series.points[0].label == "c0"


def test_a_category_series_of_more_than_60_points_is_left_out() -> None:
    assert chart_series({"groups": [_group(f"c{i}") for i in range(61)]}) == []


def test_a_long_monthly_series_keeps_the_latest_points_and_says_so() -> None:
    months = [f"{2015 + i // 12}-{i % 12 + 1:02d}" for i in range(103)]
    (series,) = chart_series({"periods": [_group(m) for m in months]})
    assert series.id == "periods"
    assert [p.label for p in series.points] == months[-MAX_POINTS:]
    assert series.title.endswith("(latest 30 of 103 months)")


def test_a_dense_weekly_series_is_left_out() -> None:
    weeks = [_group(f"2019-W{i:02d}") for i in range(1, 62)]
    assert chart_series({"periods": weeks}) == []


def test_at_most_eight_series_are_returned() -> None:
    findings = {f"s{i}": [_group("a")] for i in range(12)}
    assert [s.id for s in chart_series(findings)] == [f"s{i}" for i in range(MAX_SERIES)]


def test_the_ids_of_the_sample_result_are_the_ids_of_the_web_application() -> None:
    analyses = json.loads(SAMPLE.read_text(encoding="utf-8"))["analyses"]
    ids = {name: [s.id for s in chart_series(a["findings"])] for name, a in analyses.items()}
    assert ids["lead_time"][0] == "overall.bands"
    assert "splits.by_deposit_type.groups" in ids["cancellations"]
    assert "splits.by_market_segment.groups" in ids["cancellations"]
    assert ids["holidays"] == []
    assert all(len(found) <= MAX_SERIES for found in ids.values())
