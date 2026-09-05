"""Service CRUD des phases de suivi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.composition import (
    CompositionPoint,
    RecompositionResult,
    compute_recomposition,
)
from app.analytics.deltas import TimePoint, compute_change_between
from app.analytics.objectives import (
    Metric,
    PhaseMetricReport,
    build_phase_metric_report,
)
from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import BodyMeasurement, Phase
from app.schemas.phases import PhaseCreate, PhaseUpdate

_METRIC_COLUMN = {
    Metric.WEIGHT: ("weight_kg", "weight_target_kg"),
    Metric.BODY_FAT: ("body_fat_pct", "body_fat_target_pct"),
    Metric.MUSCLE: ("skeletal_muscle_mass_kg", "skeletal_muscle_target_kg"),
}


@dataclass(frozen=True, slots=True)
class PhaseReport:
    phase: Phase
    metrics: list[PhaseMetricReport]
    average_calories_kcal: float | None
    recomposition: RecompositionResult


async def _measurement_time_points(
    session: AsyncSession,
    column: str,
) -> list[TimePoint]:
    rows = (
        await session.execute(
            select(
                BodyMeasurement.measured_at, getattr(BodyMeasurement, column)
            ).order_by(
                BodyMeasurement.measured_at,
            ),
        )
    ).all()
    return [TimePoint(at=row[0].date(), value=row[1]) for row in rows]


async def get_phase_report(
    session: AsyncSession,
    phase_id: int,
    *,
    today: date,
) -> PhaseReport:
    phase = await get_phase(session, phase_id)
    end_date = min(phase.ends_on, today)
    days_elapsed = max((end_date - phase.starts_on).days, 0)

    metrics: list[PhaseMetricReport] = []
    for metric, (column, target_attr) in _METRIC_COLUMN.items():
        points = await _measurement_time_points(session, column)
        delta = compute_change_between(points, start=phase.starts_on, end=end_date)
        metrics.append(
            build_phase_metric_report(
                metric=metric,
                delta=delta,
                days_elapsed=days_elapsed,
                phase_kind=phase.kind,
                target=getattr(phase, target_attr),
            ),
        )

    average_calories = (
        await session.execute(
            text(
                "SELECT avg(calories) AS avg_calories FROM mv_daily_nutrition "
                "WHERE day >= :start AND day <= :end",
            ),
            {"start": phase.starts_on, "end": end_date},
        )
    ).scalar_one()

    fat_points_raw = await _measurement_time_points(session, "body_fat_mass_kg")
    lean_points_raw = await _measurement_time_points(session, "fat_free_mass_kg")
    lean_by_date = {p.at: p.value for p in lean_points_raw}
    composition_points = [
        CompositionPoint(
            at=p.at,
            fat_mass_kg=p.value,
            lean_mass_kg=lean_by_date.get(p.at),
        )
        for p in fat_points_raw
    ]
    recomposition = compute_recomposition(
        composition_points,
        start=phase.starts_on,
        end=end_date,
    )

    return PhaseReport(
        phase=phase,
        metrics=metrics,
        average_calories_kcal=average_calories,
        recomposition=recomposition,
    )


async def list_phases(session: AsyncSession) -> list[Phase]:
    query = select(Phase).order_by(Phase.starts_on.asc(), Phase.id.asc())
    return list((await session.execute(query)).scalars().all())


async def get_current_phase(session: AsyncSession, today: date) -> Phase | None:
    result = await session.execute(
        select(Phase)
        .where(Phase.starts_on <= today)
        .order_by(Phase.starts_on.desc(), Phase.id.desc())
        .limit(1),
    )
    return result.scalar_one_or_none()


async def get_phase(session: AsyncSession, phase_id: int) -> Phase:
    phase = await session.get(Phase, phase_id)
    if phase is None:
        raise NotFoundError(f"Phase {phase_id} introuvable")
    return phase


async def create_phase(session: AsyncSession, payload: PhaseCreate) -> Phase:
    phase = Phase(
        name=payload.name,
        kind=payload.kind,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        weight_target_kg=payload.weight_target_kg,
        body_fat_target_pct=payload.body_fat_target_pct,
        skeletal_muscle_target_kg=payload.skeletal_muscle_target_kg,
        daily_calories_target=payload.daily_calories_target,
        notes=payload.notes,
    )
    session.add(phase)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ConflictError("Phase déjà existante ou conflit de données.") from error
    await session.refresh(phase)
    return phase


async def update_phase(
    session: AsyncSession,
    phase_id: int,
    payload: PhaseUpdate,
) -> Phase:
    phase = await get_phase(session, phase_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(phase, field_name, value)

    starts_on = phase.starts_on
    ends_on = phase.ends_on
    if ends_on < starts_on:
        raise ValidationError("ends_on doit être postérieure ou égale à starts_on")

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ConflictError(
            "La mise à jour de phase est en conflit avec les données."
        ) from error
    await session.refresh(phase)
    return phase


async def delete_phase(session: AsyncSession, phase_id: int) -> None:
    phase = await get_phase(session, phase_id)
    await session.delete(phase)
    await session.commit()


@dataclass(frozen=True, slots=True)
class MetricSuccessRate:
    metric: Metric
    achieved_count: int
    total_count: int
    success_rate: float


async def get_transverse_report(
    session: AsyncSession, *, today: date
) -> list[MetricSuccessRate]:
    """Taux de réussite par métrique, toutes phases ayant un objectif
    confondues — l'équivalent de la page Objectifs (spec 6, /phases/report)."""
    phases = await list_phases(session)
    achieved_by_metric: dict[Metric, list[bool]] = {}
    for phase in phases:
        report = await get_phase_report(session, phase.id, today=today)
        for metric_report in report.metrics:
            objective = metric_report.objective
            if objective is None or objective.achieved is None:
                continue
            achieved_by_metric.setdefault(objective.metric, []).append(
                objective.achieved,
            )

    return [
        MetricSuccessRate(
            metric=metric,
            achieved_count=sum(flags),
            total_count=len(flags),
            success_rate=sum(flags) / len(flags),
        )
        for metric, flags in achieved_by_metric.items()
    ]
