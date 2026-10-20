"""Holiday routes called by the NF Hotel web application (openapi/market-contract.yaml)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.application.holidays import HolidayService
from app.domain.holidays import HolidayCalendar


def _body(calendar: HolidayCalendar) -> dict[str, Any]:
    return {
        "country": calendar.country,
        "source": calendar.source,
        "first_year": calendar.first_year,
        "last_year": calendar.last_year,
        "holidays": [
            {
                "name": h.name,
                "start_date": h.start_date.isoformat(),
                "end_date": h.end_date.isoformat(),
            }
            for h in calendar.holidays
        ],
    }


def holiday_router(service: HolidayService, auth: Any) -> APIRouter:  # noqa: ANN401
    """Routes for ``/api/v1/holidays``; ``auth`` is a FastAPI dependency that checks the key."""
    router = APIRouter(prefix="/api/v1/holidays", dependencies=[Depends(auth)])

    @router.get("")
    def get_holidays(year: Annotated[int | None, Query()] = None) -> dict[str, Any]:
        return _body(service.get(year))

    @router.post("/update")
    def update_holidays(
        first_year: Annotated[int | None, Query()] = None,
        last_year: Annotated[int | None, Query()] = None,
    ) -> dict[str, Any]:
        return _body(service.update(first_year, last_year))

    return router
