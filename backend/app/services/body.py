"""Service corps : lecture des mesures et séries temporelles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.deltas import Delta, TimePoint, compute_delta
from app.api.deps import DateRange
from app.errors import ValidationError
from app.models import BodyMeasurement
from app.services.phases import get_current_phase

SUMMARY_WINDOWS_DAYS = (7, 30, 90)

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


@dataclass(frozen=True, slots=True)
class BodySummary:
    latest: MeasurementRow | None
    weight_deltas: list[Delta]
    current_phase_id: int | None


async def get_summary(session: AsyncSession, today: date) -> BodySummary:
    latest_row = (
        await session.execute(
            select(BodyMeasurement).order_by(BodyMeasurement.measured_at.desc()).limit(1),
        )
    ).scalar_one_or_none()
    latest = (
        MeasurementRow(
            at=latest_row.measured_at,
            weight_kg=latest_row.weight_kg,
            body_fat_pct=latest_row.body_fat_pct,
            body_fat_mass_kg=latest_row.body_fat_mass_kg,
            skeletal_muscle_mass_kg=latest_row.skeletal_muscle_mass_kg,
            fat_free_mass_kg=latest_row.fat_free_mass_kg,
            total_body_water_kg=latest_row.total_body_water_kg,
            basal_metabolic_rate_kcal=latest_row.basal_metabolic_rate_kcal,
        )
        if latest_row is not None
        else None
    )

    weight_points = [
        TimePoint(at=row[0].date(), value=row[1])
        for row in (
            await session.execute(
                select(
                    BodyMeasurement.measured_at, BodyMeasurement.weight_kg
                ).order_by(BodyMeasurement.measured_at),
            )
        ).all()
    ]
    weight_deltas = [
        compute_delta(weight_points, reference=today, window_days=window)
        for window in SUMMARY_WINDOWS_DAYS
    ]

    current_phase = await get_current_phase(session, today)

    return BodySummary(
        latest=latest,
        weight_deltas=weight_deltas,
        current_phase_id=current_phase.id if current_phase is not None else None,
    )
