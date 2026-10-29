from pathlib import Path

import pytest

from app.domain.errors import ConfigurationError
from app.infrastructure.config import (
    AIProviderName,
    AppEnv,
    DataSource,
    LogFormat,
    LogLevel,
    Settings,
    load_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Minimum environment for the default DATA_SOURCE=api."""
    monkeypatch.setenv("MARKET_DATA_API_URL", "https://market.example.com/")


def _fails_with(monkeypatch: pytest.MonkeyPatch, **env: str) -> ConfigurationError:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ConfigurationError) as info:
        load_settings(env_file=None)
    return info.value


@pytest.mark.usefixtures("valid_env")
def test_defaults_match_documentation() -> None:
    s = load_settings(env_file=None)
    assert s.app_env is AppEnv.DEVELOPMENT
    assert s.api_host == "127.0.0.1"
    assert s.api_port == 8000
    assert s.api_token is None
    assert s.cors_allowed_origins == ()
    assert s.log_level is LogLevel.INFO
    assert s.log_format is LogFormat.JSON
    assert s.output_directory == Path("./output")
    assert s.retention_days == 7
    assert s.notebook_timeout_seconds == 1800
    assert s.max_concurrent_runs == 2
    assert s.ai_provider is AIProviderName.OLLAMA
    assert s.ai_stall_timeout_seconds == 600
    assert s.ai_total_limit_seconds == 14400
    assert s.ai_timeout_seconds is None
    assert s.ai_max_output_tokens == 32768
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model is None
    assert s.lm_studio_base_url == "http://localhost:1234"
    assert s.lm_studio_model is None
    assert s.benchmark_models == ()
    assert s.data_source is DataSource.API
    assert s.market_data_api_token is None
    assert s.market_data_csv_path == Path("./data/example")


def test_default_data_source_api_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    error = _fails_with(monkeypatch)
    assert error.variables == ("MARKET_DATA_API_URL",)
    assert "MARKET_DATA_API_URL" in str(error)


def test_csv_source_does_not_require_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_SOURCE", "csv")
    assert load_settings(env_file=None).data_source is DataSource.CSV


@pytest.mark.usefixtures("valid_env")
def test_values_are_read_case_insensitively(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_FORMAT", "CONSOLE")
    monkeypatch.setenv("AI_PROVIDER", "LMStudio")
    s = load_settings(env_file=None)
    assert (s.log_level, s.log_format, s.ai_provider) == (
        LogLevel.DEBUG,
        LogFormat.CONSOLE,
        AIProviderName.LMSTUDIO,
    )


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("APP_ENV", "staging"),
        ("AI_PROVIDER", "openai"),
        ("DATA_SOURCE", "sql"),
        ("LOG_LEVEL", "TRACE"),
        ("LOG_FORMAT", "xml"),
        ("API_PORT", "0"),
        ("API_PORT", "65536"),
        ("API_PORT", "abc"),
        ("RETENTION_DAYS", "0"),
        ("RETENTION_DAYS", "-1"),
        ("NOTEBOOK_TIMEOUT_SECONDS", "0"),
        ("AI_TIMEOUT_SECONDS", "-5"),
        ("AI_STALL_TIMEOUT_SECONDS", "0"),
        ("AI_TOTAL_TIMEOUT_SECONDS", "-1"),
        ("AI_MAX_OUTPUT_TOKENS", "0"),
        ("MAX_CONCURRENT_RUNS", "0"),
        ("OLLAMA_BASE_URL", "not a url"),
        ("LM_STUDIO_BASE_URL", "ftp://host"),
        ("MARKET_DATA_API_URL", "nope"),
    ],
)
def test_invalid_value_names_variable(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    error = _fails_with(monkeypatch, **{variable: value})
    assert variable in error.variables
    assert variable in str(error)


@pytest.mark.usefixtures("valid_env")
def test_multiple_problems_are_all_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    error = _fails_with(monkeypatch, API_PORT="0", RETENTION_DAYS="0")
    assert set(error.variables) == {"API_PORT", "RETENTION_DAYS"}


@pytest.mark.usefixtures("valid_env")
def test_ports_boundaries_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "65535")
    assert load_settings(env_file=None).api_port == 65535


@pytest.mark.usefixtures("valid_env")
def test_urls_are_normalised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://host:11434/")
    s = load_settings(env_file=None)
    assert s.ollama_base_url == "http://host:11434"
    assert s.market_data_api_url == "https://market.example.com"


@pytest.mark.usefixtures("valid_env")
def test_cors_origins_are_parsed_to_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", " https://a.example.com, https://b.example.com ,")
    s = load_settings(env_file=None)
    assert s.cors_allowed_origins == ("https://a.example.com", "https://b.example.com")


@pytest.mark.usefixtures("valid_env")
def test_benchmark_models_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BENCHMARK_MODELS", "ollama:llama3:8b, lmstudio:my-model")
    s = load_settings(env_file=None)
    assert [m.spec for m in s.benchmark_models] == ["ollama:llama3:8b", "lmstudio:my-model"]
    assert s.benchmark_models[0].model == "llama3:8b"


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize("value", ["llama3", "openai:gpt", "ollama:", ":model"])
def test_benchmark_models_invalid_entry_is_rejected(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    error = _fails_with(monkeypatch, BENCHMARK_MODELS=value)
    assert error.variables == ("BENCHMARK_MODELS",)


@pytest.mark.usefixtures("valid_env")
def test_ollama_and_lmstudio_do_not_require_model_at_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for provider in ("ollama", "lmstudio"):
        monkeypatch.setenv("AI_PROVIDER", provider)
        assert load_settings(env_file=None).ollama_model is None


def test_production_requires_token_and_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    error = _fails_with(monkeypatch, APP_ENV="production", DATA_SOURCE="csv")
    assert set(error.variables) == {"API_TOKEN", "CORS_ALLOWED_ORIGINS"}


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    error = _fails_with(
        monkeypatch,
        APP_ENV="production",
        DATA_SOURCE="csv",
        API_TOKEN="t",
        CORS_ALLOWED_ORIGINS="https://a.example.com,*",
    )
    assert error.variables == ("CORS_ALLOWED_ORIGINS",)
    assert "'*'" in str(error)


def test_production_blank_token_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    error = _fails_with(
        monkeypatch,
        APP_ENV="production",
        DATA_SOURCE="csv",
        API_TOKEN="   ",
        CORS_ALLOWED_ORIGINS="https://a.example.com",
    )
    assert error.variables == ("API_TOKEN",)


def test_production_valid_configuration_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATA_SOURCE", "csv")
    monkeypatch.setenv("API_TOKEN", "t")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.example.com")
    assert load_settings(env_file=None).app_env is AppEnv.PRODUCTION


def test_development_allows_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_SOURCE", "csv")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    assert load_settings(env_file=None).cors_allowed_origins == ("*",)


@pytest.mark.usefixtures("valid_env")
def test_settings_are_immutable() -> None:
    s = load_settings(env_file=None)
    with pytest.raises(ValueError, match="frozen"):
        s.api_port = 9  # type: ignore[misc]


@pytest.mark.usefixtures("valid_env")
def test_env_file_is_loaded(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("API_PORT=9001\nUNRELATED=1\n", encoding="utf-8")
    s = load_settings(env_file=env_file)
    assert s.api_port == 9001


@pytest.mark.usefixtures("valid_env")
def test_safe_dump_redacts_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "super-secret-1")
    monkeypatch.setenv("MARKET_DATA_API_TOKEN", "super-secret-2")
    monkeypatch.setenv("BENCHMARK_MODELS", "ollama:m")
    dump = load_settings(env_file=None).safe_dump()
    assert dump["api_token"] == "***"
    assert dump["market_data_api_token"] == "***"
    assert "super-secret" not in repr(dump)
    assert dump["benchmark_models"] == ["ollama:m"]
    assert dump["app_env"] == "development"


@pytest.mark.usefixtures("valid_env")
def test_safe_dump_keeps_unset_secrets_as_none() -> None:
    dump = load_settings(env_file=None).safe_dump()
    assert dump["api_token"] is None
    assert dump["market_data_api_token"] is None


@pytest.mark.usefixtures("valid_env")
def test_secret_is_not_exposed_by_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "super-secret-1")
    assert "super-secret-1" not in repr(load_settings(env_file=None))


def test_configuration_error_does_not_echo_secret_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = _fails_with(monkeypatch, API_TOKEN="super-secret-1", API_PORT="0")
    assert "super-secret-1" not in str(error)


def test_env_example_documents_every_variable() -> None:
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0] for line in text.splitlines() if line and not line.startswith("#")
    }
    assert documented == {name.upper() for name in Settings.model_fields}


@pytest.mark.usefixtures("valid_env")
def test_the_total_limit_is_the_new_setting_then_the_deprecated_one_then_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "1800")
    assert load_settings(env_file=None).ai_total_limit_seconds == 1800
    monkeypatch.setenv("AI_TOTAL_TIMEOUT_SECONDS", "3600")
    assert load_settings(env_file=None).ai_total_limit_seconds == 3600


@pytest.mark.usefixtures("valid_env")
def test_the_ai_limits_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_STALL_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("AI_MAX_OUTPUT_TOKENS", "1024")
    s = load_settings(env_file=None)
    assert (s.ai_stall_timeout_seconds, s.ai_max_output_tokens) == (30, 1024)


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize(
    ("provider", "variable", "expected"),
    [("ollama", "OLLAMA_MODEL", "m1"), ("lmstudio", "LM_STUDIO_MODEL", "m2")],
)
def test_the_model_is_the_one_of_the_selected_provider(
    monkeypatch: pytest.MonkeyPatch, provider: str, variable: str, expected: str
) -> None:
    monkeypatch.setenv("AI_PROVIDER", provider)
    assert load_settings(env_file=None).ai_model is None
    monkeypatch.setenv(variable, expected)
    assert load_settings(env_file=None).ai_model == expected
