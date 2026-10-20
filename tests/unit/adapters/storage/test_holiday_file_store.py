from pathlib import Path

from app.adapters.storage.holiday_file_store import FileHolidayStore
from app.domain.holidays import build_calendar


def test_round_trip(tmp_path: Path) -> None:
    store = FileHolidayStore(tmp_path / "sub" / "holidays.json")
    calendar = build_calendar(2025, 2026)
    store.save(calendar)
    assert store.load() == calendar


def test_missing_file_gives_none(tmp_path: Path) -> None:
    assert FileHolidayStore(tmp_path / "none.json").load() is None


def test_damaged_file_gives_none(tmp_path: Path) -> None:
    path = tmp_path / "holidays.json"
    path.write_text("{not json", encoding="utf-8")
    assert FileHolidayStore(path).load() is None
