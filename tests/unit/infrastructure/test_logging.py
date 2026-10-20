import json

import pytest

from app.infrastructure.config import LogFormat, LogLevel
from app.infrastructure.logging import (
    bind_context,
    bound_context,
    clear_context,
    configure_logging,
    get_logger,
    is_sensitive_key,
    redact_secrets,
)


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    parsed: dict[str, object] = json.loads(lines[-1])
    return parsed


@pytest.mark.parametrize(
    "key",
    ["token", "api_token", "API_KEY", "apikey", "password", "client_secret", "Authorization"],
)
def test_sensitive_keys_are_detected(key: str) -> None:
    assert is_sensitive_key(key)


@pytest.mark.parametrize("key", ["tokens_per_second", "job_id", "model", "author", "keyboard"])
def test_ordinary_keys_are_not_sensitive(key: str) -> None:
    assert not is_sensitive_key(key)


def test_redact_processor_handles_nested_data() -> None:
    event = {"event": "x", "headers": {"Authorization": "Bearer abc"}, "items": [{"password": "p"}]}
    result = redact_secrets(None, "info", event)
    assert result["headers"] == {"Authorization": "***"}
    assert result["items"] == [{"password": "***"}]
    assert result["event"] == "x"


def test_json_output_redacts_secrets(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(LogLevel.INFO, LogFormat.JSON)
    get_logger().info("started", api_token="abc123", model="m")
    out = _last_json(capsys)
    assert out["api_token"] == "***"
    assert out["model"] == "m"
    assert out["event"] == "started"
    assert out["level"] == "info"
    assert "timestamp" in out


def test_console_output_is_not_json_and_redacts(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(LogLevel.INFO, LogFormat.CONSOLE)
    get_logger().info("hello", password="hunter2")
    err = capsys.readouterr().err
    assert "hello" in err
    assert "hunter2" not in err
    assert not err.lstrip().startswith("{")


def test_log_level_filters_messages(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(LogLevel.WARNING, LogFormat.JSON)
    logger = get_logger()
    logger.info("hidden")
    logger.warning("shown")
    err = capsys.readouterr().err
    assert "hidden" not in err
    assert "shown" in err


def test_bound_context_appears_in_logs(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(LogLevel.INFO, LogFormat.JSON)
    bind_context(request_id="r1", job_id="j1")
    get_logger().info("evt")
    out = _last_json(capsys)
    assert out["request_id"] == "r1"
    assert out["job_id"] == "j1"


def test_clear_context_removes_values(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(LogLevel.INFO, LogFormat.JSON)
    bind_context(request_id="r1")
    clear_context()
    get_logger().info("evt")
    assert "request_id" not in _last_json(capsys)


def test_bound_context_manager_restores_state(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(LogLevel.INFO, LogFormat.JSON)
    with bound_context(job_id="j9"):
        get_logger().info("inside")
        assert _last_json(capsys)["job_id"] == "j9"
    get_logger().info("outside")
    assert "job_id" not in _last_json(capsys)
