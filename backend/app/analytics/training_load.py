"""Charge d'entraînement — TRIMP et dérive cardiaque."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Sequence

_TRIMP_SCALE = 0.64
_TRIMP_EXPONENT = 1.92
_ACUTE_WINDOW_DAYS = 7
_CHRONIC_WINDOW_DAYS = 28


@dataclass(frozen=True, slots=True)
class SessionLoadInput:
    workout_id: int
    started_at: datetime
    samples: Sequence[tuple[datetime, int | None]]
    resting_hr: int | None
    max_hr: int | None


@dataclass(frozen=True, slots=True)
class TrimpResult:
    workout_id: int
    trimp: float | None


def compute_trimp(session: SessionLoadInput) -> TrimpResult:
    if session.resting_hr is None or session.max_hr is None:
        return TrimpResult(session.workout_id, None)
    hr_range = session.max_hr - session.resting_hr
    if hr_range <= 0:
        return TrimpResult(session.workout_id, None)

    valid = sorted((s for s in session.samples if s[1] is not None), key=lambda s: s[0])
    if len(valid) < 2:
        return TrimpResult(session.workout_id, None)

    total = 0.0
    for (t0, hr0), (t1, hr1) in zip(valid, valid[1:]):
        minutes = (t1 - t0).total_seconds() / 60
        if minutes <= 0:
            continue
        mean_hr = (hr0 + hr1) / 2
        hrr = max(0.0, min(1.0, (mean_hr - session.resting_hr) / hr_range))
        total += minutes * hrr * _TRIMP_SCALE * math.exp(_TRIMP_EXPONENT * hrr)

    return TrimpResult(session.workout_id, round(total, 2))


@dataclass(frozen=True, slots=True)
class LoadPoint:
    day: date
    load: float


@dataclass(frozen=True, slots=True)
class LoadBalance:
    day: date
    acute_load: float | None
    chronic_load: float | None
    ratio: float | None


def compute_acute_chronic(daily_loads: Sequence[LoadPoint]) -> list[LoadBalance]:
    ordered = sorted(daily_loads, key=lambda p: p.day)
    load_by_day = {p.day: p.load for p in ordered}
    balances: list[LoadBalance] = []

    for point in ordered:
        acute_days = [point.day - timedelta(days=i) for i in range(_ACUTE_WINDOW_DAYS)]
        chronic_days = [point.day - timedelta(days=i) for i in range(_CHRONIC_WINDOW_DAYS)]
        acute = sum(load_by_day.get(d, 0.0) for d in acute_days) / _ACUTE_WINDOW_DAYS
        chronic = sum(load_by_day.get(d, 0.0) for d in chronic_days) / _CHRONIC_WINDOW_DAYS
        ratio = acute / chronic if chronic > 0 else None
        balances.append(LoadBalance(point.day, acute, chronic, ratio))

    return balances


@dataclass(frozen=True, slots=True)
class CardiacDrift:
    first_half_mean_hr: float | None
    second_half_mean_hr: float | None
    drift_pct: float | None


def compute_cardiac_drift(samples: Sequence[tuple[datetime, int | None]]) -> CardiacDrift:
    valid = sorted((s for s in samples if s[1] is not None), key=lambda s: s[0])
    if len(valid) < 2:
        return CardiacDrift(None, None, None)

    midpoint = len(valid) // 2
    first_half = [hr for _, hr in valid[:midpoint]]
    second_half = [hr for _, hr in valid[midpoint:]]
    if not first_half or not second_half:
        return CardiacDrift(None, None, None)

    first_mean = sum(first_half) / len(first_half)
    second_mean = sum(second_half) / len(second_half)
    drift_pct = (second_mean - first_mean) / first_mean * 100 if first_mean else None
    return CardiacDrift(first_mean, second_mean, drift_pct)
