"""Composition root: builds the service from the settings."""

from __future__ import annotations

from fastapi import FastAPI

from app.adapters.api.app import create_api
from app.adapters.storage.holiday_file_store import FileHolidayStore
from app.application.holidays import HolidayService
from app.infrastructure.config import Settings, load_settings


def build_app(settings: Settings) -> FastAPI:
    store = FileHolidayStore(settings.output_directory / "holidays.json")
    token = settings.api_token.get_secret_value() if settings.api_token else None
    return create_api(HolidayService(store), token, settings.cors_allowed_origins)


def create_app() -> FastAPI:
    """Uvicorn factory: ``uvicorn --factory app.infrastructure.main:create_app``."""
    return build_app(load_settings())
