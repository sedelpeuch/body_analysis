"""Service entraînement : séances, séries intra-séance, agrégats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.hr_zones import HrZoneTime, compute_hr_zone_times
from app.analytics.training_load import CardiacDrift, compute_cardiac_drift
from app.analytics.records import RecordEntry, WorkoutSummaryInput, compute_records
from app.analytics.splits import Split, compute_splits
from app.analytics.strength import (
    StrengthSessionVolume,
    StrengthSetInput,
    compute_session_volume,
)
from app.analytics.swim import SwimLengthInput, SwolfByStroke, compute_swolf
from app.api.deps import DateRange
from app.errors import NotFoundError, ValidationError
from app.models import StrengthSet, SwimLength, Workout, WorkoutLocation, WorkoutSample

MAX_SAMPLE_POINTS = 5000
DEFAULT_SAMPLE_POINTS = 1000
DEFAULT_PAGE_LIMIT = 50


@dataclass(frozen=True, slots=True)
class SportCount:
    sport: str
    workout_count: int


async def list_sports(session: AsyncSession) -> list[SportCount]:
    query = (
        select(Workout.sport, func.count().label("workout_count"))
        .group_by(Workout.sport)
        .order_by(Workout.sport)
    )
    rows = (await session.execute(query)).all()
    return [
        SportCount(sport=row.sport, workout_count=row.workout_count) for row in rows
    ]


async def get_workout(session: AsyncSession, workout_id: int) -> Workout:
    workout = await session.get(Workout, workout_id)
    if workout is None:
        raise NotFoundError(f"Séance {workout_id} introuvable")
    return workout


def _workout_query(sport: str | None, date_range: DateRange):
    query = select(Workout)
    if sport is not None:
        query = query.where(Workout.sport == sport)
    if date_range.start is not None:
        query = query.where(Workout.started_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(Workout.started_at <= date_range.end)
    return query


async def list_workouts(
    session: AsyncSession,
    *,
    sport: str | None,
    date_range: DateRange,
    limit: int,
    cursor: str | None,
) -> tuple[list[Workout], str | None]:
    """Pagination par curseur opaque : l'id du dernier élément de la page,
    les séances étant listées de la plus récente à la plus ancienne."""
    query = _workout_query(sport, date_range).order_by(
        Workout.started_at.desc(), Workout.id.desc()
    )
    if cursor is not None:
        try:
            cursor_id = int(cursor)
        except ValueError as error:
            raise ValidationError(f"Curseur invalide : {cursor!r}") from error
        cursor_workout = await session.get(Workout, cursor_id)
        if cursor_workout is not None:
            query = query.where(
                tuple_(Workout.started_at, Workout.id)
                < tuple_(cursor_workout.started_at, cursor_workout.id)
            )

    rows = (await session.execute(query.limit(limit + 1))).scalars().all()
    has_more = len(rows) > limit
    page_rows = list(rows[:limit])
    next_cursor = str(page_rows[-1].id) if has_more and page_rows else None
    return page_rows, next_cursor


@dataclass(frozen=True, slots=True)
class SamplePoint:
    at: object
    heart_rate: float | None
    speed_mps: float | None
    distance_m: float | None
    cadence: float | None
    altitude_m: float | None


async def get_samples(
    session: AsyncSession, workout_id: int, points: int
) -> list[SamplePoint]:
    points = max(1, min(points, MAX_SAMPLE_POINTS))
    await get_workout(session, workout_id)

    sql = text(
        """
        WITH bounds AS (
            SELECT
                extract(epoch FROM min(at)) AS start_epoch,
                extract(epoch FROM max(at)) AS end_epoch
            FROM workout_sample
            WHERE workout_id = :workout_id
        ),
        bucketed AS (
            SELECT
                width_bucket(
                    extract(epoch FROM s.at),
                    b.start_epoch,
                    b.end_epoch + 1,
                    :points
                ) AS bucket,
                s.at,
                s.heart_rate,
                s.speed_mps,
                s.distance_m,
                s.cadence
            FROM workout_sample s, bounds b
            WHERE s.workout_id = :workout_id
        )
        SELECT
            min(at) AS at,
            avg(heart_rate) AS heart_rate,
            avg(speed_mps) AS speed_mps,
            avg(distance_m) AS distance_m,
            avg(cadence) AS cadence
        FROM bucketed
        GROUP BY bucket
        ORDER BY bucket
        """
    )
    rows = (
        await session.execute(sql, {"workout_id": workout_id, "points": points})
    ).all()
    return [
        SamplePoint(
            at=row.at,
            heart_rate=row.heart_rate,
            speed_mps=row.speed_mps,
            distance_m=row.distance_m,
            cadence=row.cadence,
            altitude_m=None,
        )
        for row in rows
    ]


async def get_track(
    session: AsyncSession, workout_id: int
) -> list[tuple[float, float]]:
    await get_workout(session, workout_id)
    query = (
        select(WorkoutLocation.longitude, WorkoutLocation.latitude)
        .where(WorkoutLocation.workout_id == workout_id)
        .order_by(WorkoutLocation.at)
    )
    rows = (await session.execute(query)).all()
    return [(row.longitude, row.latitude) for row in rows]


async def get_splits(session: AsyncSession, workout_id: int, unit: str) -> list[Split]:
    await get_workout(session, workout_id)
    if unit not in {"km", "mi"}:
        raise ValidationError(f"unité inconnue : {unit!r}")
    unit_m = 1000.0 if unit == "km" else 1609.34

    query = (
        select(WorkoutSample.at, WorkoutSample.distance_m, WorkoutSample.heart_rate)
        .where(WorkoutSample.workout_id == workout_id)
        .order_by(WorkoutSample.at)
    )
    rows = (await session.execute(query)).all()
    samples = [(row.at, row.distance_m, row.heart_rate) for row in rows]
    return compute_splits(samples, unit_m=unit_m)


async def get_hr_zones(session: AsyncSession, workout_id: int) -> list[HrZoneTime]:
    workout = await get_workout(session, workout_id)
    max_hr = workout.max_hr_custom or workout.max_hr_auto
    if max_hr is None:
        raise ValidationError("max_hr indisponible pour cette séance")

    query = (
        select(WorkoutSample.at, WorkoutSample.heart_rate)
        .where(WorkoutSample.workout_id == workout_id)
        .order_by(WorkoutSample.at)
    )
    rows = (await session.execute(query)).all()
    samples = [(row.at, row.heart_rate) for row in rows]
    return compute_hr_zone_times(samples, max_hr=max_hr)


async def get_cardiac_drift(session: AsyncSession, workout_id: int) -> CardiacDrift:
    await get_workout(session, workout_id)
    query = (
        select(WorkoutSample.at, WorkoutSample.heart_rate)
        .where(WorkoutSample.workout_id == workout_id)
        .order_by(WorkoutSample.at)
    )
    rows = (await session.execute(query)).all()
    samples = [(row.at, row.heart_rate) for row in rows]
    return compute_cardiac_drift(samples)


async def get_swim(session: AsyncSession, workout_id: int) -> list[SwolfByStroke]:
    await get_workout(session, workout_id)
    query = (
        select(SwimLength)
        .where(SwimLength.workout_id == workout_id)
        .order_by(SwimLength.idx)
    )
    rows = (await session.execute(query)).scalars().all()
    lengths = [
        SwimLengthInput(
            idx=row.idx,
            duration_ms=row.duration_ms,
            stroke_count=row.stroke_count,
            stroke_type=row.stroke_type,
        )
        for row in rows
    ]
    return compute_swolf(lengths)


@dataclass(frozen=True, slots=True)
class StrengthResult:
    sets: list[StrengthSet]
    volume: StrengthSessionVolume


async def get_strength(session: AsyncSession, workout_id: int) -> StrengthResult:
    await get_workout(session, workout_id)
    query = (
        select(StrengthSet)
        .where(StrengthSet.workout_id == workout_id)
        .order_by(StrengthSet.idx)
    )
    rows = (await session.execute(query)).scalars().all()
    inputs = [
        StrengthSetInput(
            idx=row.idx,
            reps=row.reps,
            weight_kg=row.weight_kg,
            duration_s=row.duration_s,
        )
        for row in rows
    ]
    return StrengthResult(sets=list(rows), volume=compute_session_volume(inputs))


@dataclass(frozen=True, slots=True)
class WorkoutStats:
    session_count: int
    total_duration_ms: int
    total_distance_m: float
    total_calories_kcal: float


async def get_stats(
    session: AsyncSession, sport: str | None, date_range: DateRange
) -> WorkoutStats:
    subquery = _workout_query(sport, date_range).subquery()
    query = select(
        func.count(),
        func.coalesce(func.sum(subquery.c.duration_ms), 0),
        func.coalesce(func.sum(subquery.c.distance_m), 0.0),
        func.coalesce(func.sum(subquery.c.calories_kcal), 0.0),
    ).select_from(subquery)
    row = (await session.execute(query)).one()
    return WorkoutStats(
        session_count=row[0],
        total_duration_ms=row[1],
        total_distance_m=row[2],
        total_calories_kcal=row[3],
    )


async def get_records(session: AsyncSession, sport: str | None) -> list[RecordEntry]:
    query = select(Workout)
    if sport is not None:
        query = query.where(Workout.sport == sport)
    rows = (await session.execute(query)).scalars().all()
    inputs = [
        WorkoutSummaryInput(
            id=row.id,
            started_at=row.started_at,
            distance_m=row.distance_m,
            duration_ms=row.duration_ms,
            calories_kcal=row.calories_kcal,
            mean_speed_mps=row.mean_speed_mps,
        )
        for row in rows
    ]
    return compute_records(inputs)


@dataclass(frozen=True, slots=True)
class WorkoutCalendarCell:
    day: date
    value: float | None


_CALENDAR_METRICS = {
    "session_count": "session_count",
    "duration_ms": "duration_ms",
    "calories_kcal": "calories_kcal",
    "distance_m": "distance_m",
}


async def get_calendar(
    session: AsyncSession, metric: str, year: int
) -> list[WorkoutCalendarCell]:
    if metric not in _CALENDAR_METRICS:
        raise ValidationError(f"métrique inconnue : {metric!r}")
    column = _CALENDAR_METRICS[metric]
    sql = text(
        f"SELECT day, {column} FROM mv_daily_training "
        "WHERE extract(year FROM day) = :year ORDER BY day",
    )
    rows = (await session.execute(sql, {"year": year})).all()
    return [
        WorkoutCalendarCell(day=row.day, value=getattr(row, column)) for row in rows
    ]
