"""Recomposition corporelle en kilogrammes — spec 5.2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True, slots=True)
class CompositionPoint:
    at: date
    fat_mass_kg: float | None
    lean_mass_kg: float | None


@dataclass(frozen=True, slots=True)
class RecompositionResult:
    fat_mass_delta_kg: float | None
    lean_mass_delta_kg: float | None


def _nearest_value(
    points: Sequence[CompositionPoint], target: date, field: str
) -> float | None:
    candidates = [p for p in points if getattr(p, field) is not None and p.at <= target]
    if not candidates:
        return None
    return getattr(max(candidates, key=lambda p: p.at), field)


def compute_recomposition(
    points: Sequence[CompositionPoint], *, start: date, end: date
) -> RecompositionResult:
    fat_start = _nearest_value(points, start, "fat_mass_kg")
    fat_end = _nearest_value(points, end, "fat_mass_kg")
    lean_start = _nearest_value(points, start, "lean_mass_kg")
    lean_end = _nearest_value(points, end, "lean_mass_kg")

    fat_delta = None
    if fat_start is not None and fat_end is not None:
        fat_delta = round(fat_end - fat_start, 10)

    lean_delta = None
    if lean_start is not None and lean_end is not None:
        lean_delta = round(lean_end - lean_start, 10)

    return RecompositionResult(
        fat_mass_delta_kg=fat_delta,
        lean_mass_delta_kg=lean_delta,
    )
