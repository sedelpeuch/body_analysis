"""Service corps : lecture des mesures et séries temporelles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.errors import ValidationError
from app.models import BodyMeasurement

METRIC_COLUMNS = {
    "weight": "weight_kg",
    "body_fat": "body_fat_pct",
    "muscle": "skeletal_muscle_mass_kg",
}


@dataclass(frozen=True, slots=True)
class MeasurementRow:
    at: datetime
    weight_kg: float | None
    body_fat_pct: float | None
    body_fat_mass_kg: float | None
    skeletal_muscle_mass_kg: float | None
    fat_free_mass_kg: float | None
    total_body_water_kg: float | None
    basal_metabolic_rate_kcal: float | None


def _measurement_query(date_range: DateRange):
    query = select(BodyMeasurement).order_by(BodyMeasurement.measured_at)
    if date_range.start is not None:
        query = query.where(BodyMeasurement.measured_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(BodyMeasurement.measured_at <= date_range.end)
    return query


async def list_measurements(
    session: AsyncSession,
    date_range: DateRange,
) -> list[MeasurementRow]:
    rows = (await session.execute(_measurement_query(date_range))).scalars().all()
    return [
        MeasurementRow(
            at=row.measured_at,
            weight_kg=row.weight_kg,
            body_fat_pct=row.body_fat_pct,
            body_fat_mass_kg=row.body_fat_mass_kg,
            skeletal_muscle_mass_kg=row.skeletal_muscle_mass_kg,
            fat_free_mass_kg=row.fat_free_mass_kg,
            total_body_water_kg=row.total_body_water_kg,
            basal_metabolic_rate_kcal=row.basal_metabolic_rate_kcal,
        )
        for row in rows
    ]


@dataclass(frozen=True, slots=True)
class TimeseriesPoint:
    at: date
    value: float | None


async def _raw_series(
    session: AsyncSession,
    date_range: DateRange,
    column: str,
) -> list[TimeseriesPoint]:
    query = select(
        BodyMeasurement.measured_at, getattr(BodyMeasurement, column)
    ).order_by(
        BodyMeasurement.measured_at,
    )
    if date_range.start is not None:
        query = query.where(BodyMeasurement.measured_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(BodyMeasurement.measured_at <= date_range.end)
    rows = (await session.execute(query)).all()
    return [TimeseriesPoint(at=row[0].date(), value=row[1]) for row in rows]


async def _daily_series(
    session: AsyncSession,
    date_range: DateRange,
    column: str,
) -> list[TimeseriesPoint]:
    where_parts: list[str] = []
    params: dict[str, date] = {}
    if date_range.start is not None:
        where_parts.append("day >= :start")
        params["start"] = date_range.start
    if date_range.end is not None:
        where_parts.append("day <= :end")
        params["end"] = date_range.end

    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = text(f"SELECT day, {column} FROM mv_daily_body{where_clause} ORDER BY day")
    rows = (await session.execute(sql, params)).all()
    return [TimeseriesPoint(at=row.day, value=getattr(row, column)) for row in rows]


async def get_timeseries(
    session: AsyncSession,
    date_range: DateRange,
    metrics: list[str],
    resolution: str,
) -> dict[str, list[TimeseriesPoint]]:
    if resolution not in {"raw", "daily"}:
        raise ValidationError(f"resolution inconnue : {resolution!r}")
    unknown = set(metrics) - set(METRIC_COLUMNS)
    if unknown:
        raise ValidationError(f"métriques inconnues : {sorted(unknown)}")

    result: dict[str, list[TimeseriesPoint]] = {}
    for metric in metrics:
        column = METRIC_COLUMNS[metric]
        if resolution == "raw":
            result[metric] = await _raw_series(session, date_range, column)
        else:
            result[metric] = await _daily_series(session, date_range, column)
    return result


@dataclass(frozen=True, slots=True)
class CalendarCell:
    day: date
    value: float | None


async def get_calendar(
    session: AsyncSession, metric: str, year: int
) -> list[CalendarCell]:
    if metric not in METRIC_COLUMNS:
        raise ValidationError(f"métrique inconnue : {metric!r}")
    column = METRIC_COLUMNS[metric]
    sql = text(
        f"SELECT day, {column} FROM mv_daily_body "
        "WHERE extract(year FROM day) = :year ORDER BY day",
    )
    rows = (await session.execute(sql, {"year": year})).all()
    return [CalendarCell(day=row.day, value=getattr(row, column)) for row in rows]
