"""Tests des splits au kilomètre — interpolation entre échantillons.

Vitesse constante 3 m/s, échantillon toutes les 10 s : la distance cumulée
franchit 1000 m entre t=330 (990 m) et t=340 (1020 m). Le passage au km
s'interpole à t = 330 + 10*(1000-990)/(1020-990) = 333.333... s.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.splits import compute_splits

T0 = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def _constant_speed_samples(n: int, *, speed_mps: float, step_s: int):
    return [
        (T0 + timedelta(seconds=i * step_s), i * step_s * speed_mps, None)
        for i in range(n)
    ]


def test_compute_splits_interpolates_kilometer_crossing() -> None:
    samples = _constant_speed_samples(35, speed_mps=3.0, step_s=10)

    splits = compute_splits(samples, unit_m=1000.0)

    assert len(splits) == 2
    first = splits[0]
    assert first.index == 1
    assert first.distance_m == pytest.approx(1000.0)
    assert first.duration_s == pytest.approx(333.333, abs=0.01)
    assert first.pace_s_per_km == pytest.approx(333.333, abs=0.01)


def test_compute_splits_final_partial_segment() -> None:
    samples = _constant_speed_samples(35, speed_mps=3.0, step_s=10)

    splits = compute_splits(samples, unit_m=1000.0)

    partial = splits[1]
    assert partial.index == 2
    assert partial.distance_m == pytest.approx(20.0, abs=0.01)
    assert partial.duration_s == pytest.approx(6.667, abs=0.01)


def test_compute_splits_averages_heart_rate_within_split() -> None:
    samples = [
        (T0, 0.0, 140),
        (T0 + timedelta(seconds=100), 500.0, 150),
        (T0 + timedelta(seconds=200), 1000.0, 160),
    ]

    splits = compute_splits(samples, unit_m=1000.0)

    assert splits[0].mean_heart_rate == pytest.approx((140 + 150) / 2)


def test_compute_splits_on_empty_samples_returns_empty_list() -> None:
    assert compute_splits([], unit_m=1000.0) == []


def test_compute_splits_ignores_samples_without_distance() -> None:
    samples = [(T0, None, 140), (T0 + timedelta(seconds=10), 30.0, 145)]

    splits = compute_splits(samples, unit_m=1000.0)

    assert len(splits) == 1
    assert splits[0].distance_m == pytest.approx(30.0)
