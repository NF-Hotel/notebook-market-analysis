"""Application settings loaded from environment variables and an optional ``.env`` file.

Model names (``OLLAMA_MODEL``, ``LM_STUDIO_MODEL``) are deliberately not required at load
time, even when the matching provider is selected: only the market analysis notebook needs
them, so the check happens where the model is used, not at startup.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import ErrorDetails, PydanticCustomError
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.domain.errors import ConfigurationError

REDACTED = "***"
DEFAULT_AI_TOTAL_TIMEOUT_SECONDS = 14400.0
_URL_ADAPTER: TypeAdapter[AnyHttpUrl] = TypeAdapter(AnyHttpUrl)


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class AIProviderName(StrEnum):
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"


class DataSource(StrEnum):
    API = "api"
    CSV = "csv"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


class BenchmarkModel(BaseModel):
    """One ``provider:model`` entry of ``BENCHMARK_MODELS``."""

    model_config = ConfigDict(frozen=True)

    provider: AIProviderName
    model: str

    @property
    def spec(self) -> str:
        return f"{self.provider.value}:{self.model}"

    @classmethod
    def parse(cls, entry: str) -> BenchmarkModel:
        provider, sep, model = entry.partition(":")
        provider = provider.strip().lower()
        model = model.strip()
        if not sep or not provider or not model:
            raise ValueError(f"'{entry}' must have the form provider:model")
        try:
            return cls(provider=AIProviderName(provider), model=model)
        except ValueError:
            allowed = ", ".join(p.value for p in AIProviderName)
            raise ValueError(f"unknown provider '{provider}' (allowed: {allowed})") from None


def _split_csv(value: object) -> object:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return value


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _validate_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        url = _URL_ADAPTER.validate_python(value.strip())
    except ValidationError:
        raise ValueError("must be a valid http(s) URL") from None
    return str(url).rstrip("/")


class Settings(BaseSettings):
    """Immutable, validated application configuration."""

    model_config = SettingsConfigDict(
        frozen=True,
        extra="ignore",
        env_ignore_empty=True,
        case_sensitive=False,
    )

    app_env: AppEnv = AppEnv.DEVELOPMENT
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_token: SecretStr | None = None
    cors_allowed_origins: Annotated[tuple[str, ...], NoDecode] = ()

    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat = LogFormat.JSON

    output_directory: Path = Path("./output")
    retention_days: int = Field(default=7, gt=0)
    notebook_timeout_seconds: int = Field(default=1800, gt=0)
    max_concurrent_runs: int = Field(default=2, ge=1)

    ai_provider: AIProviderName = AIProviderName.OLLAMA
    # Seconds without a new token before a model request is given up.
    ai_stall_timeout_seconds: float = Field(default=600, gt=0)
    # Seconds of one whole model request, however many tokens arrive.
    ai_total_timeout_seconds: float | None = Field(default=None, gt=0)
    # Deprecated: the old single timeout; it still sets the total limit when that is not set.
    ai_timeout_seconds: float | None = Field(default=None, gt=0)
    ai_max_output_tokens: int = Field(default=32768, ge=1)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str | None = None
    lm_studio_base_url: str = "http://localhost:1234"
    lm_studio_model: str | None = None
    benchmark_models: Annotated[tuple[BenchmarkModel, ...], NoDecode] = ()

    data_source: DataSource = DataSource.API
    market_data_api_url: str | None = None
    market_data_api_token: SecretStr | None = None
    market_data_csv_path: Path = Path("./data/example")

    @field_validator("ai_total_timeout_seconds", "ai_timeout_seconds", mode="before")
    @classmethod
    def _blank_number(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("app_env", "ai_provider", "data_source", "log_format", mode="before")
    @classmethod
    def _lower_enum(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_enum(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("api_token", "market_data_api_token", mode="before")
    @classmethod
    def _blank_secret(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("ollama_model", "lm_studio_model", "market_data_api_url", mode="before")
    @classmethod
    def _blank_optional(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> object:
        return _split_csv(value)

    @field_validator("benchmark_models", mode="before")
    @classmethod
    def _parse_benchmark_models(cls, value: object) -> object:
        parts = _split_csv(value)
        if not isinstance(parts, tuple):
            return parts
        return tuple(BenchmarkModel.parse(str(part)) for part in parts)

    @field_validator("ollama_base_url", "lm_studio_base_url", "market_data_api_url")
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        return _validate_url(value)

    @model_validator(mode="after")
    def _check_cross_field_rules(self) -> Settings:
        problems: list[tuple[str, str]] = []
        if self.app_env is AppEnv.PRODUCTION:
            if self.api_token is None:
                problems.append(("API_TOKEN", "is required when APP_ENV=production"))
            if not self.cors_allowed_origins:
                problems.append(
                    ("CORS_ALLOWED_ORIGINS", "must list explicit origins when APP_ENV=production")
                )
            elif "*" in self.cors_allowed_origins:
                problems.append(
                    ("CORS_ALLOWED_ORIGINS", "must not contain '*' when APP_ENV=production")
                )
        if self.data_source is DataSource.API and self.market_data_api_url is None:
            problems.append(("MARKET_DATA_API_URL", "is required when DATA_SOURCE=api"))
        if problems:
            raise PydanticCustomError(
                "configuration",
                "Invalid configuration: " + "; ".join(f"{v} {m}" for v, m in problems),
                {"variables": [v for v, _ in problems], "problems": problems},
            )
        return self

    @property
    def ai_total_limit_seconds(self) -> float:
        """The total limit of one model request: the new setting, else the deprecated one."""
        for value in (self.ai_total_timeout_seconds, self.ai_timeout_seconds):
            if value is not None:
                return value
        return DEFAULT_AI_TOTAL_TIMEOUT_SECONDS

    @property
    def ai_model(self) -> str | None:
        """The model name of the selected provider; None when it is not set."""
        if self.ai_provider is AIProviderName.OLLAMA:
            return self.ollama_model
        return self.lm_studio_model

    def safe_dump(self) -> dict[str, Any]:
        """Return the settings as plain JSON-friendly data with secrets redacted."""
        data: dict[str, Any] = self.model_dump(mode="json")
        for name in ("api_token", "market_data_api_token"):
            data[name] = REDACTED if getattr(self, name) is not None else None
        data["benchmark_models"] = [m.spec for m in self.benchmark_models]
        data["cors_allowed_origins"] = list(self.cors_allowed_origins)
        return data


def _describe(error: ErrorDetails) -> tuple[list[str], list[str]]:
    """Map one pydantic error to (variable names, messages) without echoing input values."""
    ctx = error.get("ctx") or {}
    if "problems" in ctx:
        problems: list[tuple[str, str]] = ctx["problems"]
        return [v for v, _ in problems], [f"{v} {m}" for v, m in problems]
    loc = error.get("loc") or ()
    variable = str(loc[0]).upper() if loc else "SETTINGS"
    return [variable], [f"{variable}: {error.get('msg', 'invalid value')}"]


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Load and validate settings; raise ``ConfigurationError`` naming offending variables."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        variables: list[str] = []
        messages: list[str] = []
        for error in exc.errors(include_input=False, include_url=False):
            names, texts = _describe(error)
            variables.extend(names)
            messages.extend(texts)
        unique = tuple(dict.fromkeys(variables))
        raise ConfigurationError(
            "Invalid configuration: " + "; ".join(messages), variables=unique
        ) from None
