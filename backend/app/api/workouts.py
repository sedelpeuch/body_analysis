"""Routes entraînement : séances, séries intra-séance, agrégats.

Les routes statiques (/stats, /records, /calendar) sont déclarées avant
/{workout_id} : FastAPI matche les routes dans l'ordre d'enregistrement, et
un {workout_id}: int déclaré en premier intercepterait "stats" avant même
d'échouer la conversion en entier.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DateRangeDep, DbSession
from app.schemas.common import CursorPage
from app.schemas.workouts import (
    CardiacDriftOut,
    HrZoneOut,
    RecordOut,
    SamplePointOut,
    SplitOut,
    SportOut,
    StrengthOut,
    StrengthSetOut,
    SwolfByStrokeOut,
    TrackOut,
    WorkoutCalendarCellOut,
    WorkoutDetailOut,
    WorkoutStatsOut,
    WorkoutSummaryOut,
)
from app.services import workouts as workouts_service
from app.services.workouts import DEFAULT_PAGE_LIMIT, DEFAULT_SAMPLE_POINTS

sports_router = APIRouter(prefix="/sports", tags=["entraînement"])
router = APIRouter(prefix="/workouts", tags=["entraînement"])


@sports_router.get("", response_model=list[SportOut])
async def list_sports(session: DbSession):
    rows = await workouts_service.list_sports(session)
    return [SportOut.model_validate(r) for r in rows]


@router.get("", response_model=CursorPage[WorkoutSummaryOut])
async def list_workouts(
    session: DbSession,
    date_range: DateRangeDep,
    sport: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=200),
    cursor: str | None = Query(default=None),
):
    rows, next_cursor = await workouts_service.list_workouts(
        session, sport=sport, date_range=date_range, limit=limit, cursor=cursor
    )
    return CursorPage[WorkoutSummaryOut](
        items=[WorkoutSummaryOut.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )


@router.get("/stats", response_model=WorkoutStatsOut)
async def get_stats(
    session: DbSession,
    date_range: DateRangeDep,
    sport: str | None = Query(default=None),
):
    stats = await workouts_service.get_stats(session, sport, date_range)
    return WorkoutStatsOut.model_validate(stats)


@router.get("/records", response_model=list[RecordOut])
async def get_records(session: DbSession, sport: str | None = Query(default=None)):
    records = await workouts_service.get_records(session, sport)
    return [RecordOut.model_validate(r) for r in records]


@router.get("/calendar", response_model=list[WorkoutCalendarCellOut])
async def get_calendar(
    session: DbSession,
    metric: str = Query(default="session_count"),
    year: int = Query(...),
):
    cells = await workouts_service.get_calendar(session, metric, year)
    return [WorkoutCalendarCellOut.model_validate(c) for c in cells]


@router.get("/{workout_id}", response_model=WorkoutDetailOut)
async def get_workout(workout_id: int, session: DbSession):
    workout = await workouts_service.get_workout(session, workout_id)
    return WorkoutDetailOut.model_validate(workout)


@router.get("/{workout_id}/samples", response_model=list[SamplePointOut])
async def get_samples(
    workout_id: int,
    session: DbSession,
    points: int = Query(default=DEFAULT_SAMPLE_POINTS, ge=1),
):
    samples = await workouts_service.get_samples(session, workout_id, points)
    return [SamplePointOut.model_validate(s) for s in samples]


@router.get("/{workout_id}/track", response_model=TrackOut)
async def get_track(workout_id: int, session: DbSession):
    coordinates = await workouts_service.get_track(session, workout_id)
    return TrackOut(coordinates=coordinates)


@router.get("/{workout_id}/splits", response_model=list[SplitOut])
async def get_splits(
    workout_id: int, session: DbSession, unit: str = Query(default="km")
):
    splits = await workouts_service.get_splits(session, workout_id, unit)
    return [SplitOut.model_validate(s) for s in splits]


@router.get("/{workout_id}/hr-zones", response_model=list[HrZoneOut])
async def get_hr_zones(workout_id: int, session: DbSession):
    zones = await workouts_service.get_hr_zones(session, workout_id)
    return [HrZoneOut.model_validate(z) for z in zones]


@router.get("/{workout_id}/cardiac-drift", response_model=CardiacDriftOut)
async def get_cardiac_drift(workout_id: int, session: DbSession):
    drift = await workouts_service.get_cardiac_drift(session, workout_id)
    return CardiacDriftOut.model_validate(drift)


@router.get("/{workout_id}/swim", response_model=list[SwolfByStrokeOut])
async def get_swim(workout_id: int, session: DbSession):
    swim = await workouts_service.get_swim(session, workout_id)
    return [SwolfByStrokeOut.model_validate(s) for s in swim]


@router.get("/{workout_id}/strength", response_model=StrengthOut)
async def get_strength(workout_id: int, session: DbSession):
    result = await workouts_service.get_strength(session, workout_id)
    return StrengthOut(
        sets=[StrengthSetOut.model_validate(s) for s in result.sets],
        set_count=result.volume.set_count,
        total_volume_kg=result.volume.total_volume_kg,
        total_reps=result.volume.total_reps,
    )
