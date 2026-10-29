"""The FastAPI application of the market analysis service."""

from __future__ import annotations

import hmac
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adapters.api.v1.holidays import holiday_router
from app.adapters.api.v1.market_analysis import RUNS_PATH_PREFIX, market_analysis_router
from app.application.holidays import HolidayService
from app.application.runs import GetRun, GetRunResult, StartRun
from app.domain.errors import (
    AppError,
    InvalidRequest,
    ResultNotReady,
    RunAlreadyActive,
    RunFailed,
    RunNotFound,
)

API_KEY_HEADER = "X-API-Key"
_STATUS_OF_ERROR: dict[type[AppError], int] = {
    InvalidRequest: 400,
    RunNotFound: 404,
    RunAlreadyActive: 409,
    ResultNotReady: 409,
    RunFailed: 409,
}


def _problem(status: int, code: str, message: str = "") -> JSONResponse:
    body = {"code": code}
    if message:
        body["message"] = message
    return JSONResponse(body, status_code=status)


def create_api(
    holidays: HolidayService,
    start_run: StartRun,
    get_run: GetRun,
    get_run_result: GetRunResult,
    api_token: str | None,
    cors_allowed_origins: tuple[str, ...] = (),
) -> FastAPI:
    """Build the app. Without a token every route except ``/health`` answers 401."""
    app = FastAPI(title="NF Hotel market analysis", docs_url=None, redoc_url=None)

    if cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_allowed_origins),
            allow_methods=["GET", "POST"],
            allow_headers=[API_KEY_HEADER],
        )

    def require_key(
        x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
    ) -> None:
        if (
            not api_token
            or not x_api_key
            or not hmac.compare_digest(x_api_key.encode(), api_token.encode())
        ):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return _problem(exc.status_code, "unauthorized" if exc.status_code == 401 else "error")

    @app.exception_handler(RequestValidationError)
    async def _bad_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        # The run paths answer 400 with a stable code; the holiday paths keep FastAPI's 422.
        if request.url.path.startswith(RUNS_PATH_PREFIX):
            return _problem(400, InvalidRequest.code, "a parameter of the request is not valid")
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        status = next((s for t, s in _STATUS_OF_ERROR.items() if isinstance(exc, t)), None)
        if status is None:
            return _problem(500, exc.code)
        return _problem(status, exc.code, exc.message)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    app.include_router(holiday_router(holidays, require_key))
    app.include_router(market_analysis_router(start_run, get_run, get_run_result, require_key))
    return app
