import json
from pathlib import Path

import pytest

from app.adapters.storage.run_file_store import FileRunStore
from app.domain.run import Run
from tests.unit.run_fakes import T0

RUN_ID = "00000000-0000-4000-8000-000000000001"


def _run(run_id: str = RUN_ID) -> Run:
    return Run.queued(run_id, T0, True)


def test_a_saved_run_is_loaded_with_all_its_fields(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path)
    failed = _run().start(T0).fail(T0, "analysis_failed")
    store.save(failed)
    assert store.load(RUN_ID) == failed


def test_the_state_is_kept_in_state_json_in_a_folder_of_the_run(tmp_path: Path) -> None:
    FileRunStore(tmp_path).save(_run())
    state = json.loads((tmp_path / RUN_ID / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "queued"
    assert list(tmp_path.glob("**/*.tmp")) == []


def test_the_result_is_kept_in_result_json(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path)
    store.save_result(RUN_ID, {"schema_version": "1.1"})
    assert (tmp_path / RUN_ID / "result.json").is_file()
    assert store.load_result(RUN_ID) == {"schema_version": "1.1"}


def test_an_unknown_run_has_no_state_and_no_result(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path)
    assert store.load(RUN_ID) is None
    assert store.load_result(RUN_ID) is None


@pytest.mark.parametrize("run_id", ["..", "../x", "a/b", "not-a-uuid", RUN_ID.upper()])
def test_an_id_that_is_not_a_uuid_is_never_read(tmp_path: Path, run_id: str) -> None:
    store = FileRunStore(tmp_path)
    assert store.load(run_id) is None
    assert store.load_result(run_id) is None


def test_a_damaged_state_file_is_an_unknown_run(tmp_path: Path) -> None:
    (tmp_path / RUN_ID).mkdir()
    (tmp_path / RUN_ID / "state.json").write_text("{not json", encoding="utf-8")
    assert FileRunStore(tmp_path).load(RUN_ID) is None


def test_active_runs_are_only_the_queued_and_the_running(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path)
    other = "00000000-0000-4000-8000-000000000002"
    third = "00000000-0000-4000-8000-000000000003"
    store.save(_run())
    store.save(_run(other).start(T0))
    store.save(_run(third).start(T0).complete(T0))
    assert {r.run_id for r in store.active_runs()} == {RUN_ID, other}


def test_there_are_no_active_runs_before_the_folder_exists(tmp_path: Path) -> None:
    assert FileRunStore(tmp_path / "missing").active_runs() == []


def test_a_result_with_nan_is_refused_and_leaves_no_file(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path)
    with pytest.raises(ValueError, match="Out of range"):
        store.save_result(RUN_ID, {"value": float("nan")})
    assert store.load_result(RUN_ID) is None
    assert list((tmp_path / RUN_ID).glob("*")) == []
