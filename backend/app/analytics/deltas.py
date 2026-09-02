"""Deltas génériques sur une série temporelle pouvant contenir des trous."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence


@dataclass(frozen=True, slots=True)
class TimePoint:
    at: date
    value: float | None


@dataclass(frozen=True, slots=True)
class Delta:
    window_days: int
    start_value: float | None
    end_value: float | None
    change: float | None


def find_nearest_at_or_before(
    points: Sequence[TimePoint], target: date
) -> TimePoint | None:
    candidates = [p for p in points if p.value is not None and p.at <= target]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.at)


def _delta_between(
    points: Sequence[TimePoint], *, start: date, end: date, window_days: int
) -> Delta:
    start_point = find_nearest_at_or_before(points, start)
    end_point = find_nearest_at_or_before(points, end)
    change = None
    if start_point is not None and end_point is not None:
        change = end_point.value - start_point.value
    return Delta(
        window_days=window_days,
        start_value=start_point.value if start_point else None,
        end_value=end_point.value if end_point else None,
        change=change,
    )


def compute_delta(
    points: Sequence[TimePoint], *, reference: date, window_days: int
) -> Delta:
    start = reference - timedelta(days=window_days)
    return _delta_between(points, start=start, end=reference, window_days=window_days)


def compute_change_between(
    points: Sequence[TimePoint], *, start: date, end: date
) -> Delta:
    return _delta_between(
        points,
        start=start,
        end=end,
        window_days=(end - start).days,
    )
