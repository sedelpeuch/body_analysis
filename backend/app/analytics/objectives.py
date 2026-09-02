"""Sens d'atteinte des objectifs de phase — spec section 6."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from app.analytics.deltas import Delta
from app.models.phase import PhaseKind


class Metric(enum.StrEnum):
    WEIGHT = "weight"
    BODY_FAT = "body_fat"
    MUSCLE = "muscle"


class Direction(enum.StrEnum):
    UP = "up"
    DOWN = "down"


_WEIGHT_DIRECTION_BY_KIND: dict[PhaseKind, Direction] = {
    PhaseKind.CUT: Direction.DOWN,
    PhaseKind.BULK: Direction.UP,
    PhaseKind.MAINTAIN: Direction.DOWN,
    PhaseKind.FREE: Direction.DOWN,
}


def achievement_direction(phase_kind: PhaseKind, metric: Metric) -> Direction:
    if metric is Metric.MUSCLE:
        return Direction.UP
    if metric is Metric.BODY_FAT:
        return Direction.DOWN
    return _WEIGHT_DIRECTION_BY_KIND[phase_kind]


@dataclass(frozen=True, slots=True)
class ObjectiveCheck:
    metric: Metric
    target: float
    current: float | None
    direction: Direction
    achieved: bool | None
    remaining: float | None


def evaluate_objective(
    *, phase_kind: PhaseKind, metric: Metric, target: float, current: float | None
) -> ObjectiveCheck:
    direction = achievement_direction(phase_kind, metric)
    if current is None:
        return ObjectiveCheck(
            metric=metric,
            target=target,
            current=None,
            direction=direction,
            achieved=None,
            remaining=None,
        )
    achieved = current <= target if direction is Direction.DOWN else current >= target
    remaining = target - current if direction is Direction.DOWN else current - target
    return ObjectiveCheck(
        metric=metric,
        target=target,
        current=current,
        direction=direction,
        achieved=achieved,
        remaining=remaining,
    )


@dataclass(frozen=True, slots=True)
class PhaseMetricReport:
    metric: Metric
    start_value: float | None
    end_value: float | None
    change: float | None
    change_pct: float | None
    monthly_rate: float | None
    objective: ObjectiveCheck | None


_DAYS_PER_MONTH = 30.44


def build_phase_metric_report(
    *,
    metric: Metric,
    delta: Delta,
    days_elapsed: int,
    phase_kind: PhaseKind,
    target: float | None,
) -> PhaseMetricReport:
    change_pct = None
    if delta.change is not None and delta.start_value not in (None, 0):
        change_pct = delta.change / delta.start_value * 100

    monthly_rate = None
    if delta.change is not None and days_elapsed > 0:
        monthly_rate = delta.change / days_elapsed * _DAYS_PER_MONTH

    objective = None
    if target is not None:
        objective = evaluate_objective(
            phase_kind=phase_kind,
            metric=metric,
            target=target,
            current=delta.end_value,
        )

    return PhaseMetricReport(
        metric=metric,
        start_value=delta.start_value,
        end_value=delta.end_value,
        change=delta.change,
        change_pct=change_pct,
        monthly_rate=monthly_rate,
        objective=objective,
    )
