"""Service des analyses transverses — spec section 5 et 6."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.energy import (
    DailyBmr,
    DailyIntake,
    EnergyBalanceDay,
    TdeeEstimate,
    WeighIn,
    compute_energy_balance,
    estimate_tdee,
)
from app.analytics.training_load import (
    LoadBalance,
    LoadPoint,
    SessionLoadInput,
    compute_acute_chronic,
    compute_trimp,
)
from app.api.deps import DateRange
from app.models import Workout, WorkoutSample
from app.services.phases import get_phase


async def _resolve_range(
    session: AsyncSession, *, phase_id: int | None, date_range: DateRange
) -> tuple[date | None, date | None]:
    if phase_id is not None:
        phase = await get_phase(session, phase_id)
        return phase.starts_on, phase.ends_on
    return date_range.start, date_range.end


@dataclass(frozen=True, slots=True)
class CompositionPoint:
    day: date
    body_fat_mass_kg: float | None
    fat_free_mass_kg: float | None
    skeletal_muscle_mass_kg: float | None
    total_body_water_kg: float | None
    basal_metabolic_rate_kcal: float | None


async def get_composition(
    session: AsyncSession, date_range: DateRange
) -> list[CompositionPoint]:
    where_parts: list[str] = []
    params: dict[str, date] = {}
    if date_range.start is not None:
        where_parts.append("day >= :start")
        params["start"] = date_range.start
    if date_range.end is not None:
        where_parts.append("day <= :end")
        params["end"] = date_range.end
    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

    sql = text(
        "SELECT day, body_fat_mass_kg, fat_free_mass_kg, skeletal_muscle_mass_kg, "
        "total_body_water_kg, basal_metabolic_rate_kcal "
        f"FROM mv_daily_body{where_clause} ORDER BY day",
    )
    rows = (await session.execute(sql, params)).all()
    return [
        CompositionPoint(
            day=row.day,
            body_fat_mass_kg=row.body_fat_mass_kg,
            fat_free_mass_kg=row.fat_free_mass_kg,
            skeletal_muscle_mass_kg=row.skeletal_muscle_mass_kg,
            total_body_water_kg=row.total_body_water_kg,
            basal_metabolic_rate_kcal=row.basal_metabolic_rate_kcal,
        )
        for row in rows
    ]


async def _daily_intakes(
    session: AsyncSession, start: date | None, end: date | None
) -> list[DailyIntake]:
    where_parts: list[str] = []
    params: dict[str, date] = {}
    if start is not None:
        where_parts.append("day >= :start")
        params["start"] = start
    if end is not None:
        where_parts.append("day <= :end")
        params["end"] = end
    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = text(
        f"SELECT day, calories FROM mv_daily_nutrition{where_clause} ORDER BY day",
    )
    rows = (await session.execute(sql, params)).all()
    return [DailyIntake(day=row.day, calories=row.calories) for row in rows]


async def _weigh_ins(
    session: AsyncSession, start: date | None, end: date | None
) -> list[WeighIn]:
    where_parts: list[str] = []
    params: dict[str, date] = {}
    if start is not None:
        where_parts.append("day >= :start")
        params["start"] = start
    if end is not None:
        where_parts.append("day <= :end")
        params["end"] = end
    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = text(f"SELECT day, weight_kg FROM mv_daily_body{where_clause} ORDER BY day")
    rows = (await session.execute(sql, params)).all()
    return [WeighIn(day=row.day, weight_kg=row.weight_kg) for row in rows]


async def get_tdee(
    session: AsyncSession, *, phase_id: int | None, date_range: DateRange
) -> TdeeEstimate:
    start, end = await _resolve_range(session, phase_id=phase_id, date_range=date_range)
    intakes = await _daily_intakes(session, start, end)
    weigh_ins = await _weigh_ins(session, start, end)
    return estimate_tdee(intakes, weigh_ins)


async def _bmr_points(
    session: AsyncSession, start: date | None, end: date | None
) -> list[DailyBmr]:
    where_parts: list[str] = []
    params: dict[str, date] = {}
    if start is not None:
        where_parts.append("day >= :start")
        params["start"] = start
    if end is not None:
        where_parts.append("day <= :end")
        params["end"] = end
    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = text(
        f"SELECT day, basal_metabolic_rate_kcal FROM mv_daily_body{where_clause} "
        "ORDER BY day",
    )
    rows = (await session.execute(sql, params)).all()
    return [
        DailyBmr(day=row.day, bmr_kcal=row.basal_metabolic_rate_kcal) for row in rows
    ]


async def _workout_kcal_by_day(
    session: AsyncSession, start: date | None, end: date | None
) -> dict[date, float]:
    where_parts: list[str] = []
    params: dict[str, date] = {}
    if start is not None:
        where_parts.append("day >= :start")
        params["start"] = start
    if end is not None:
        where_parts.append("day <= :end")
        params["end"] = end
    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = text(
        f"SELECT day, calories_kcal FROM mv_daily_training{where_clause} ORDER BY day",
    )
    rows = (await session.execute(sql, params)).all()
    return {row.day: row.calories_kcal or 0.0 for row in rows}


async def get_energy_balance(
    session: AsyncSession, date_range: DateRange
) -> list[EnergyBalanceDay]:
    intakes = await _daily_intakes(session, date_range.start, date_range.end)
    bmr_points = await _bmr_points(session, date_range.start, date_range.end)
    workout_kcal = await _workout_kcal_by_day(session, date_range.start, date_range.end)
    return compute_energy_balance(intakes, bmr_points, workout_kcal)


@dataclass(frozen=True, slots=True)
class RestingHrPoint:
    day: date
    resting_hr: int | None


async def get_resting_hr(
    session: AsyncSession, date_range: DateRange
) -> list[RestingHrPoint]:
    """Moyenne des resting_hr Samsung par séance, par jour civil Europe/Paris."""
    where_parts: list[str] = ["resting_hr IS NOT NULL"]
    params: dict[str, date] = {}
    if date_range.start is not None:
        where_parts.append("started_at >= :start")
        params["start"] = date_range.start
    if date_range.end is not None:
        where_parts.append("started_at <= :end")
        params["end"] = date_range.end
    where_clause = " AND ".join(where_parts)
    sql = text(
        "SELECT (started_at AT TIME ZONE 'Europe/Paris')::date AS day, "
        "avg(resting_hr) AS resting_hr "
        f"FROM workout WHERE {where_clause} GROUP BY 1 ORDER BY 1",
    )
    rows = (await session.execute(sql, params)).all()
    return [
        RestingHrPoint(
            day=row.day, resting_hr=round(row.resting_hr) if row.resting_hr else None
        )
        for row in rows
    ]


async def get_training_load(
    session: AsyncSession, date_range: DateRange
) -> list[LoadBalance]:
    query = select(Workout).where(Workout.has_samples.is_(True))
    query = query.order_by(Workout.started_at)
    if date_range.start is not None:
        query = query.where(Workout.started_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(Workout.started_at <= date_range.end)
    workouts = (await session.execute(query)).scalars().all()
    if not workouts:
        return []

    # Une requête pour l'ensemble des séances plutôt qu'une par séance :
    # sur l'historique complet (~4 700 séances), l'aller-retour réseau par
    # requête dominait largement le calcul lui-même (24 s contre <2 s ici).
    workout_ids = [w.id for w in workouts]
    samples_rows = (
        await session.execute(
            select(
                WorkoutSample.workout_id, WorkoutSample.at, WorkoutSample.heart_rate
            ).where(WorkoutSample.workout_id.in_(workout_ids)),
        )
    ).all()
    samples_by_workout: dict[int, list[tuple[datetime, int | None]]] = {}
    for row in samples_rows:
        samples_by_workout.setdefault(row.workout_id, []).append(
            (row.at, row.heart_rate)
        )

    load_by_day: dict[date, float] = {}
    for workout in workouts:
        samples = samples_by_workout.get(workout.id)
        if not samples:
            continue
        trimp = compute_trimp(
            SessionLoadInput(
                workout_id=workout.id,
                started_at=workout.started_at,
                samples=samples,
                resting_hr=workout.resting_hr,
                max_hr=workout.max_hr_custom or workout.max_hr_auto,
            ),
        )
        if trimp.trimp is None:
            continue
        day = workout.started_at.date()
        load_by_day[day] = load_by_day.get(day, 0.0) + trimp.trimp

    if not load_by_day:
        return []
    daily_loads = [LoadPoint(day=day, load=load) for day, load in load_by_day.items()]
    return compute_acute_chronic(daily_loads)
