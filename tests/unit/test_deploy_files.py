"""The container settings of MIL-001 criterion 8, read from the Dockerfile and the compose file."""

from pathlib import Path

from tests.unit.compose_file import compose_service, mem_limit_bytes

DOCKERFILE = Path(__file__).parents[2] / "Dockerfile"


def _dockerfile_lines() -> list[str]:
    return DOCKERFILE.read_text(encoding="utf-8").splitlines()


def test_the_compose_file_publishes_no_host_port() -> None:
    service = compose_service()
    assert "ports" not in service
    assert service["expose"] == ["8000"]


def test_the_container_has_a_read_only_file_system_and_no_capabilities() -> None:
    service = compose_service()
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]


def test_the_container_has_a_memory_limit() -> None:
    assert mem_limit_bytes() > 0


def test_the_image_runs_as_a_user_that_is_not_root() -> None:
    users = [line.split(maxsplit=1)[1] for line in _dockerfile_lines() if line.startswith("USER ")]
    assert users
    assert users[-1].strip() not in {"root", "0"}


def test_the_image_builds_from_the_repository_alone() -> None:
    text = "\n".join(_dockerfile_lines()).lower()
    for fetch in ("git clone", "curl ", "wget ", "add http"):
        assert fetch not in text
