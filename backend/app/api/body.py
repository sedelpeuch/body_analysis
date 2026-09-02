"""Routes de lecture de la famille corps."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DateRangeDep, DbSession
from app.schemas.body import CalendarCellOut, MeasurementOut, TimeseriesPointOut
from app.services import body as body_service

router = APIRouter(prefix="/body", tags=["corps"])


@router.get("/measurements", response_model=list[MeasurementOut])
async def get_measurements(session: DbSession, date_range: DateRangeDep):
    rows = await body_service.list_measurements(session, date_range)
    return [MeasurementOut.model_validate(r) for r in rows]


@router.get("/timeseries", response_model=dict[str, list[TimeseriesPointOut]])
async def get_timeseries(
    session: DbSession,
    date_range: DateRangeDep,
    metrics: str = Query(..., description="liste séparée par des virgules"),
    resolution: str = Query(default="raw"),
):
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    series = await body_service.get_timeseries(session, date_range, metric_list, resolution)
    return {
        metric: [TimeseriesPointOut.model_validate(p) for p in points]
        for metric, points in series.items()
    }


@router.get("/calendar", response_model=list[CalendarCellOut])
async def get_calendar(
    session: DbSession,
    metric: str = Query(...),
    year: int = Query(...),
):
    cells = await body_service.get_calendar(session, metric, year)
    return [CalendarCellOut.model_validate(c) for c in cells]
