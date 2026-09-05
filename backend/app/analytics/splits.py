"""Splits au kilomètre par interpolation linéaire."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Split:
    index: int
    distance_m: float
    duration_s: float
    pace_s_per_km: float | None
    mean_heart_rate: float | None


def _mean(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def compute_splits(
    samples: Sequence[tuple[datetime, float | None, int | None]],
    *,
    unit_m: float = 1000.0,
) -> list[Split]:
    points = sorted(
        ((at, dist, hr) for at, dist, hr in samples if dist is not None),
        key=lambda p: p[0],
    )
    if not points:
        return []

    splits: list[Split] = []
    index = 1
    seg_start_t = points[0][0]
    seg_start_dist = 0.0
    hr_acc: list[int] = []
    target = unit_m

    for (at0, d0, hr0), (at1, d1, hr1) in zip(points, points[1:]):
        if hr0 is not None:
            hr_acc.append(hr0)
        while d1 >= target > d0:
            fraction = (target - d0) / (d1 - d0) if d1 != d0 else 0.0
            cross_t = at0 + (at1 - at0) * fraction
            duration_s = (cross_t - seg_start_t).total_seconds()
            distance_m = target - seg_start_dist
            pace = duration_s / (distance_m / 1000) if distance_m > 0 else None
            splits.append(
                Split(index, distance_m, duration_s, pace, _mean(hr_acc)),
            )
            index += 1
            seg_start_t = cross_t
            seg_start_dist = target
            hr_acc = []
            target += unit_m

    last_at, last_dist, last_hr = points[-1]
    if last_hr is not None:
        hr_acc.append(last_hr)
    if last_dist > seg_start_dist:
        duration_s = (last_at - seg_start_t).total_seconds()
        distance_m = last_dist - seg_start_dist
        pace = duration_s / (distance_m / 1000) if distance_m > 0 else None
        splits.append(Split(index, distance_m, duration_s, pace, _mean(hr_acc)))

    return splits
