"""Run routes called by the NF Hotel web application (openapi/market-contract.yaml)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, ValidationError

from app.application.runs import GetRun, GetRunResult, StartRun, StartRunCommand
from app.domain.booking import Booking
from app.domain.errors import InvalidRequest
from app.domain.period import Period
from app.domain.run import Run

RUNS_PATH_PREFIX = "/api/v1/market-analysis"
_MAX_REPORTED_ERRORS = 5


class _Strict(BaseModel):
    """A body model: no unknown field and no coercion (``"no"`` is not a boolean)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class BookingModel(_Strict):
    booking_id: int
    hotel: str
    is_canceled: bool
    arrival_date: date
    stays_in_weekend_nights: NonNegativeInt
    stays_in_week_nights: NonNegativeInt
    country: str
    lead_time: NonNegativeInt | None = None
    booking_date: date | None = None
    adults: NonNegativeInt | None = None
    children: NonNegativeInt | None = None
    babies: NonNegativeInt | None = None
    meal: str | None = None
    market_segment: str | None = None
    is_repeated_guest: bool | None = None
    previous_cancellations: NonNegativeInt | None = None
    assigned_room_type: str | None = None
    booking_changes: NonNegativeInt | None = None
    deposit_type: str | None = None
    customer_type: str | None = None
    required_car_parking_spaces: NonNegativeInt | None = None
    total_of_special_requests: NonNegativeInt | None = None
    price_per_night: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None

    def to_domain(self) -> Booking:
        data = self.model_dump()
        price = data.pop("price_per_night")
        return Booking(**data, price_per_night=None if price is None else Decimal(str(price)))


class PeriodModel(_Strict):
    first_date: date
    last_date: date


class RunRequestModel(_Strict):
    room_count: int = Field(ge=1)
    period: PeriodModel | None = None
    bookings: list[BookingModel] = Field(min_length=1)


def _describe(error: ValidationError) -> str:
    """Where and why the body was refused; the values sent are left out."""
    problems = [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors(include_input=False, include_url=False, include_context=False)
    ]
    shown = "; ".join(problems[:_MAX_REPORTED_ERRORS])
    return f"the body is not a valid run request ({shown})"


def _command_of(body: bytes, insights: bool) -> StartRunCommand:
    try:
        request = RunRequestModel.model_validate_json(body, strict=True)
    except ValidationError as error:
        raise InvalidRequest(_describe(error)) from None
    period = None
    if request.period is not None:
        period = Period(request.period.first_date, request.period.last_date)
    return StartRunCommand(
        [b.to_domain() for b in request.bookings], request.room_count, period, insights
    )


def _state_body(run: Run) -> dict[str, Any]:
    body: dict[str, Any] = {
        "run_id": run.run_id,
        "state": run.state.value,
        "created_at": run.created_at.isoformat(),
    }
    if run.started_at:
        body["started_at"] = run.started_at.isoformat()
    if run.finished_at:
        body["finished_at"] = run.finished_at.isoformat()
    if run.error_code:
        body["error_code"] = run.error_code
    return body


def market_analysis_router(
    start_run: StartRun,
    get_run: GetRun,
    get_run_result: GetRunResult,
    auth: Any,  # noqa: ANN401 - a FastAPI dependency
) -> APIRouter:
    """Routes for ``/api/v1/market-analysis/runs``; ``auth`` is the dependency for the key."""
    router = APIRouter(prefix=f"{RUNS_PATH_PREFIX}/runs", dependencies=[Depends(auth)])

    def start(body: bytes, insights: bool) -> JSONResponse:
        run = start_run.start(_command_of(body, insights))
        return JSONResponse(_state_body(run), status_code=202)

    @router.post("", status_code=202)
    async def post_run(request: Request, insights: Annotated[bool, Query()] = True) -> JSONResponse:
        # The body is read raw so that it is checked strictly against the contract.
        return await run_in_threadpool(start, await request.body(), insights)

    @router.get("/{run_id}")
    def get_state(run_id: str) -> dict[str, Any]:
        return _state_body(get_run.get(run_id))

    @router.get("/{run_id}/result")
    def get_result(run_id: str) -> JSONResponse:
        return JSONResponse(get_run_result.get(run_id))

    return router
