"""Volume et progression en musculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True, slots=True)
class StrengthSetInput:
    idx: int
    reps: int | None
    weight_kg: float | None
    duration_s: float | None


@dataclass(frozen=True, slots=True)
class StrengthSessionVolume:
    set_count: int
    total_volume_kg: float | None
    total_reps: int | None


def compute_session_volume(sets: Sequence[StrengthSetInput]) -> StrengthSessionVolume:
    if not sets:
        return StrengthSessionVolume(set_count=0, total_volume_kg=None, total_reps=None)

    usable = [s for s in sets if s.reps is not None and s.weight_kg is not None]
    reps_known = [s for s in sets if s.reps is not None]

    return StrengthSessionVolume(
        set_count=len(sets),
        total_volume_kg=sum(s.reps * s.weight_kg for s in usable) if usable else None,
        total_reps=sum(s.reps for s in reps_known) if reps_known else None,
    )


@dataclass(frozen=True, slots=True)
class ProgressionPoint:
    at: date
    total_volume_kg: float | None


def compute_progression(
    sessions: Sequence[tuple[date, Sequence[StrengthSetInput]]],
) -> list[ProgressionPoint]:
    return [
        ProgressionPoint(at=day, total_volume_kg=compute_session_volume(sets).total_volume_kg)
        for day, sets in sessions
    ]
