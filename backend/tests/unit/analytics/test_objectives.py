"""Tests du sens d'atteinte des objectifs — spec 6.

Règle : en sèche, le poids cible est un plancher atteint en descendant ; en
prise de masse, un plafond atteint en montant ; la masse musculaire
s'atteint toujours vers le haut ; la masse grasse toujours vers le bas.
"""

import pytest

from app.analytics.deltas import Delta
from app.analytics.objectives import (
    Direction,
    Metric,
    achievement_direction,
    build_phase_metric_report,
    evaluate_objective,
)
from app.models.phase import PhaseKind


@pytest.mark.parametrize(
    ("phase_kind", "expected"),
    [(PhaseKind.CUT, Direction.DOWN), (PhaseKind.BULK, Direction.UP)],
)
def test_weight_direction_depends_on_phase_kind(
    phase_kind: PhaseKind, expected: Direction
) -> None:
    assert achievement_direction(phase_kind, Metric.WEIGHT) is expected


@pytest.mark.parametrize("phase_kind", list(PhaseKind))
def test_muscle_direction_is_always_up(phase_kind: PhaseKind) -> None:
    assert achievement_direction(phase_kind, Metric.MUSCLE) is Direction.UP


@pytest.mark.parametrize("phase_kind", list(PhaseKind))
def test_body_fat_direction_is_always_down(phase_kind: PhaseKind) -> None:
    assert achievement_direction(phase_kind, Metric.BODY_FAT) is Direction.DOWN


def test_cut_weight_target_achieved_when_current_at_or_below_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.CUT, metric=Metric.WEIGHT, target=75.0, current=74.5
    )

    assert check.direction is Direction.DOWN
    assert check.achieved is True


def test_cut_weight_target_not_achieved_when_current_above_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.CUT, metric=Metric.WEIGHT, target=75.0, current=76.2
    )

    assert check.achieved is False


def test_bulk_weight_target_achieved_when_current_at_or_above_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.BULK, metric=Metric.WEIGHT, target=85.0, current=85.3
    )

    assert check.achieved is True


def test_bulk_weight_target_not_achieved_when_current_below_target() -> None:
    check = evaluate_objective(
        phase_kind=PhaseKind.BULK, metric=Metric.WEIGHT, target=85.0, current=83.0
    )

    assert check.achieved is False


@pytest.mark.parametrize("phase_kind", [PhaseKind.CUT, PhaseKind.BULK])
def test_muscle_target_achieved_upward_regardless_of_phase_kind(
    phase_kind: PhaseKind,
) -> None:
    """Verrou explicite de la règle : la sèche inverse le sens du poids mais
    jamais celui du muscle."""
    achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.MUSCLE, target=35.0, current=35.4
    )
    not_achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.MUSCLE, target=35.0, current=34.1
    )

    assert achieved.achieved is True
    assert not_achieved.achieved is False


@pytest.mark.parametrize("phase_kind", [PhaseKind.CUT, PhaseKind.BULK])
def test_body_fat_target_achieved_downward_regardless_of_phase_kind(
    phase_kind: PhaseKind,
) -> None:
    achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.BODY_FAT, target=12.0, current=11.5
    )
    not_achieved = evaluate_objective(
        phase_kind=phase_kind, metric=Metric.BODY_FAT, target=12.0, current=13.0
    )

    assert achieved.achieved is True
    assert not_achieved.achieved is False


def test_unknown_current_value_leaves_achieved_undetermined() -> None:
    """260 mesures réelles n'ont ni masse grasse ni muscle : l'objectif ne
    doit jamais se déclarer manqué faute de donnée, il doit rester None."""
    check = evaluate_objective(
        phase_kind=PhaseKind.CUT, metric=Metric.BODY_FAT, target=12.0, current=None
    )

    assert check.achieved is None
    assert check.remaining is None


def test_build_phase_metric_report_computes_rate_and_pct() -> None:
    delta = Delta(window_days=61, start_value=80.0, end_value=77.0, change=-3.0)

    report = build_phase_metric_report(
        metric=Metric.WEIGHT,
        delta=delta,
        days_elapsed=61,
        phase_kind=PhaseKind.CUT,
        target=75.0,
    )

    assert report.change == -3.0
    assert report.change_pct == pytest.approx(-3.75, rel=1e-3)
    assert report.monthly_rate == pytest.approx(-1.4967, rel=1e-3)
    assert report.objective is not None
    assert report.objective.achieved is False


def test_build_phase_metric_report_without_target_has_no_objective() -> None:
    delta = Delta(window_days=30, start_value=80.0, end_value=79.0, change=-1.0)

    report = build_phase_metric_report(
        metric=Metric.WEIGHT,
        delta=delta,
        days_elapsed=30,
        phase_kind=PhaseKind.CUT,
        target=None,
    )

    assert report.objective is None
