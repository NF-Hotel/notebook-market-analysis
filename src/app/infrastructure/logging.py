"""Structured logging setup with secret redaction and request/job context binding."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from typing import Any

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

from app.infrastructure.config import LogFormat, LogLevel

REDACTED = "***"

_SENSITIVE_KEY = re.compile(
    r"(^|[_\-\s])(token|api[_\-]?key|password|passwd|secret|authorization|credentials?)$",
    re.IGNORECASE,
)


def is_sensitive_key(key: str) -> bool:
    """Return True if a log field name looks like it holds a secret."""
    return bool(_SENSITIVE_KEY.search(key)) or key.lower() in {"authorization", "apikey"}


def _redact_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {k: REDACTED if _is_sensitive(k) else _redact_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return type(value)(_redact_value(v) for v in value)
    return value


def _is_sensitive(key: object) -> bool:
    return isinstance(key, str) and is_sensitive_key(key)


def redact_secrets(
    logger: WrappedLogger, method_name: str, event_dict: MutableMapping[str, Any]
) -> EventDict:
    """structlog processor replacing values of sensitive keys (recursively) with ``***``."""
    return {k: REDACTED if _is_sensitive(k) else _redact_value(v) for k, v in event_dict.items()}


def _renderer(log_format: LogFormat) -> Processor:
    if log_format is LogFormat.JSON:
        return structlog.processors.JSONRenderer(default=str)
    return structlog.dev.ConsoleRenderer(colors=False)


def configure_logging(
    level: LogLevel = LogLevel.INFO, log_format: LogFormat = LogFormat.JSON
) -> None:
    """Configure structlog globally; output goes to stderr."""
    numeric_level = logging.getLevelNamesMapping()[level.value]
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
        redact_secrets,
        _renderer(log_format),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.WriteLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.typing.FilteringBoundLogger:
    """Return a structlog logger."""
    logger: structlog.typing.FilteringBoundLogger = structlog.get_logger(name)
    return logger


def bind_context(*, request_id: str | None = None, job_id: str | None = None) -> None:
    """Bind ``request_id`` and/or ``job_id`` to every log line in the current context."""
    values = {"request_id": request_id, "job_id": job_id}
    structlog.contextvars.bind_contextvars(**{k: v for k, v in values.items() if v is not None})


def clear_context() -> None:
    """Remove all bound context values."""
    structlog.contextvars.clear_contextvars()


@contextmanager
def bound_context(*, request_id: str | None = None, job_id: str | None = None) -> Iterator[None]:
    """Bind context for the duration of a ``with`` block, then restore the previous state."""
    values = {"request_id": request_id, "job_id": job_id}
    tokens = structlog.contextvars.bind_contextvars(
        **{k: v for k, v in values.items() if v is not None}
    )
    try:
        yield
    finally:
        structlog.contextvars.reset_contextvars(**tokens)
