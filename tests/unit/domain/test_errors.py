import pytest

from app.domain import errors
from app.domain.errors import AppError, ConfigurationError

ALL_ERRORS: dict[type[AppError], str] = {
    errors.InvalidRequest: "invalid_request",
    errors.NotebookNotFound: "notebook_not_found",
    errors.RunNotFound: "run_not_found",
    errors.RunAlreadyActive: "run_active",
    errors.ResultNotReady: "result_not_ready",
    errors.RunFailed: "run_failed",
    errors.InvalidRunTransition: "invalid_run_transition",
    errors.AIProviderUnavailable: "ai_provider_unavailable",
    errors.ModelNotLoaded: "model_not_loaded",
    errors.AIProviderTimeout: "ai_provider_timeout",
    errors.AIInvalidResponse: "ai_invalid_response",
    errors.NotebookExecutionFailed: "notebook_execution_failed",
    errors.ReportGenerationFailed: "report_generation_failed",
    errors.ConfigurationError: "configuration_error",
}


@pytest.mark.parametrize(("error_type", "code"), list(ALL_ERRORS.items()))
def test_error_has_stable_code(error_type: type[AppError], code: str) -> None:
    assert error_type.code == code
    assert issubclass(error_type, AppError)


def test_error_codes_are_unique() -> None:
    codes = [*ALL_ERRORS.values(), AppError.code]
    assert len(codes) == len(set(codes))


def test_error_message_is_used_for_str() -> None:
    assert str(errors.RunNotFound("run 42 missing")) == "run 42 missing"


def test_error_message_defaults_to_code() -> None:
    assert errors.RunNotFound().message == "run_not_found"


def test_configuration_error_carries_variables() -> None:
    error = ConfigurationError("bad", variables=("API_PORT",))
    assert error.variables == ("API_PORT",)
