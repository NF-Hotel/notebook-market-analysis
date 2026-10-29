"""Composition root: builds the service from the settings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import FastAPI

from app.adapters.ai.lm_studio import LMStudioModelClient
from app.adapters.ai.ollama import OllamaModelClient
from app.adapters.api.app import create_api
from app.adapters.executor.thread_task_runner import ThreadTaskRunner
from app.adapters.storage.holiday_file_store import FileHolidayStore
from app.adapters.storage.run_file_store import FileRunStore
from app.application.holidays import HolidayService
from app.application.insights import UnconfiguredInsightProvider
from app.application.model_insights import ModelInsightProvider
from app.application.ports.insight_provider import InsightProvider
from app.application.ports.model_client import ModelClient, TimeLimits
from app.application.runs import ExecuteRun, GetRun, GetRunResult, RecoverInterruptedRuns, StartRun
from app.infrastructure.config import AIProviderName, Settings, load_settings

RUNS_FOLDER = "runs"


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


def _model_client(settings: Settings, model: str) -> ModelClient:
    if settings.ai_provider is AIProviderName.OLLAMA:
        return OllamaModelClient(settings.ollama_base_url, model)
    return LMStudioModelClient(settings.lm_studio_base_url, model)


def build_insight_provider(settings: Settings) -> InsightProvider:
    """The model of the selected provider; the unconfigured one when no model name is set."""
    model = settings.ai_model
    if model is None:
        return UnconfiguredInsightProvider()
    limits = TimeLimits(settings.ai_stall_timeout_seconds, settings.ai_total_limit_seconds)
    return ModelInsightProvider(
        _model_client(settings, model), limits, settings.ai_max_output_tokens, _now
    )


def build_app(settings: Settings) -> FastAPI:
    holidays = HolidayService(FileHolidayStore(settings.output_directory / "holidays.json"))
    runs = FileRunStore(settings.output_directory / RUNS_FOLDER)
    # A run left queued or running by a restart will never finish.
    RecoverInterruptedRuns(runs, _now).recover()
    execute = ExecuteRun(runs, holidays, build_insight_provider(settings), _now, _new_id)
    start = StartRun(runs, ThreadTaskRunner(), execute, _now, _new_id)
    token = settings.api_token.get_secret_value() if settings.api_token else None
    return create_api(
        holidays,
        start,
        GetRun(runs),
        GetRunResult(runs),
        token,
        settings.cors_allowed_origins,
    )


def create_app() -> FastAPI:
    """Uvicorn factory: ``uvicorn --factory app.infrastructure.main:create_app``."""
    return build_app(load_settings())
