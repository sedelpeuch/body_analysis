"""Records par sport."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WorkoutSummaryInput:
    id: int
    started_at: datetime
    distance_m: float | None
    duration_ms: int | None
    calories_kcal: float | None
    mean_speed_mps: float | None


@dataclass(frozen=True, slots=True)
class RecordEntry:
    label: str
    workout_id: int
    value: float
    at: datetime


_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Distance la plus longue", "distance_m"),
    ("Durée la plus longue", "duration_ms"),
    ("Vitesse moyenne la plus élevée", "mean_speed_mps"),
    ("Calories les plus élevées", "calories_kcal"),
)


def compute_records(workouts: Sequence[WorkoutSummaryInput]) -> list[RecordEntry]:
    records: list[RecordEntry] = []
    for label, field in _CATEGORIES:
        eligible = [w for w in workouts if getattr(w, field) is not None]
        if not eligible:
            continue
        best = max(eligible, key=lambda w: getattr(w, field))
        records.append(
            RecordEntry(label, best.id, getattr(best, field), best.started_at)
        )
    return records
