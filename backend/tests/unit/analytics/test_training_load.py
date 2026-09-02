"""Tests de la charge d'entraînement — spec 5.4."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.analytics.training_load import (
    CardiacDrift,
    LoadPoint,
    SessionLoadInput,
    compute_acute_chronic,
    compute_cardiac_drift,
    compute_trimp,
)

T0 = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def test_compute_trimp_matches_hand_derived_value() -> None:
    session = SessionLoadInput(
        workout_id=1,
        started_at=T0,
        samples=[(T0, 150), (T0 + timedelta(minutes=10), 150)],
        resting_hr=50,
        max_hr=190,
    )

    result = compute_trimp(session)

    assert result.trimp == pytest.approx(18.01, abs=0.05)


def test_compute_trimp_is_none_without_resting_or_max_hr() -> None:
    session = SessionLoadInput(
        workout_id=1, started_at=T0, samples=[(T0, 150)], resting_hr=None, max_hr=190
    )

    assert compute_trimp(session).trimp is None


def test_compute_trimp_is_none_without_enough_samples() -> None:
    session = SessionLoadInput(
        workout_id=1, started_at=T0, samples=[(T0, 150)], resting_hr=50, max_hr=190
    )

    assert compute_trimp(session).trimp is None


def test_compute_acute_chronic_averages_over_7_and_28_days() -> None:
    start = date(2026, 1, 1)
    daily_loads = [LoadPoint(day=start + timedelta(days=i), load=100.0) for i in range(28)]

    balances = compute_acute_chronic(daily_loads)
    last = balances[-1]

    assert last.acute_load == pytest.approx(100.0)
    assert last.chronic_load == pytest.approx(100.0)
    assert last.ratio == pytest.approx(1.0)


def test_compute_acute_chronic_ratio_above_one_signals_spike() -> None:
    start = date(2026, 1, 1)
    daily_loads = [LoadPoint(day=start + timedelta(days=i), load=50.0) for i in range(21)]
    daily_loads += [LoadPoint(day=start + timedelta(days=i), load=150.0) for i in range(21, 28)]

    balances = {b.day: b for b in compute_acute_chronic(daily_loads)}
    last_day = start + timedelta(days=27)

    assert balances[last_day].ratio > 1.0


def test_compute_cardiac_drift_compares_first_and_second_half() -> None:
    samples = [
        (T0, 130),
        (T0 + timedelta(minutes=10), 130),
        (T0 + timedelta(minutes=20), 150),
        (T0 + timedelta(minutes=30), 150),
    ]

    drift = compute_cardiac_drift(samples)

    assert drift.first_half_mean_hr == pytest.approx(130.0)
    assert drift.second_half_mean_hr == pytest.approx(150.0)
    assert drift.drift_pct == pytest.approx((150.0 - 130.0) / 130.0 * 100)


def test_compute_cardiac_drift_on_empty_samples_is_none() -> None:
    drift = compute_cardiac_drift([])

    assert drift == CardiacDrift(None, None, None)
