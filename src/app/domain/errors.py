"""Domain error types with stable, machine-readable codes."""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors.

    Each subclass has a stable ``code`` that clients and logs can rely on.
    """

    code: str = "app_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message or self.code

    def __str__(self) -> str:
        return self.message


class InvalidRequest(AppError):
    code = "invalid_request"


class NotebookNotFound(AppError):
    code = "notebook_not_found"


class RunNotFound(AppError):
    code = "run_not_found"


class RunAlreadyActive(AppError):
    code = "run_active"


class ResultNotReady(AppError):
    code = "result_not_ready"


class RunFailed(AppError):
    code = "run_failed"


class InvalidRunTransition(AppError):
    code = "invalid_run_transition"


class AIProviderUnavailable(AppError):
    code = "ai_provider_unavailable"


class ModelNotLoaded(AppError):
    code = "model_not_loaded"


class AIProviderTimeout(AppError):
    code = "ai_provider_timeout"


class AIInvalidResponse(AppError):
    code = "ai_invalid_response"


class NotebookExecutionFailed(AppError):
    code = "notebook_execution_failed"


class ReportGenerationFailed(AppError):
    code = "report_generation_failed"


class ConfigurationError(AppError):
    """Invalid or missing configuration; names the offending variables."""

    code = "configuration_error"

    def __init__(self, message: str, variables: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.variables = variables
