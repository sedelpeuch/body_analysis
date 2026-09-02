"""Tests du volume et de la progression en musculation — spec 4.8."""

from datetime import date

import pytest

from app.analytics.strength import (
    ProgressionPoint,
    StrengthSetInput,
    compute_progression,
    compute_session_volume,
)


def test_compute_session_volume_sums_reps_times_weight() -> None:
    sets = [
        StrengthSetInput(idx=0, reps=10, weight_kg=50.0, duration_s=30.0),
        StrengthSetInput(idx=1, reps=8, weight_kg=55.0, duration_s=32.0),
    ]

    volume = compute_session_volume(sets)

    assert volume.set_count == 2
    assert volume.total_volume_kg == pytest.approx(10 * 50.0 + 8 * 55.0)
    assert volume.total_reps == 18


def test_compute_session_volume_skips_sets_missing_reps_or_weight() -> None:
    sets = [
        StrengthSetInput(idx=0, reps=10, weight_kg=None, duration_s=30.0),
        StrengthSetInput(idx=1, reps=8, weight_kg=55.0, duration_s=32.0),
    ]

    volume = compute_session_volume(sets)

    assert volume.set_count == 2
    assert volume.total_volume_kg == pytest.approx(8 * 55.0)


def test_compute_session_volume_on_empty_sets() -> None:
    volume = compute_session_volume([])

    assert volume.set_count == 0
    assert volume.total_volume_kg is None
    assert volume.total_reps is None


def test_compute_progression_returns_one_point_per_session() -> None:
    sessions = [
        (date(2026, 1, 1), [StrengthSetInput(idx=0, reps=10, weight_kg=50.0, duration_s=30.0)]),
        (date(2026, 1, 8), [StrengthSetInput(idx=0, reps=10, weight_kg=55.0, duration_s=30.0)]),
    ]

    progression = compute_progression(sessions)

    assert progression == [
        ProgressionPoint(at=date(2026, 1, 1), total_volume_kg=500.0),
        ProgressionPoint(at=date(2026, 1, 8), total_volume_kg=550.0),
    ]
