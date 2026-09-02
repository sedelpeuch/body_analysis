"""Zones cardiaques calculées à partir de max_hr et des échantillons."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

_ZONE_DEFINITIONS = (
    (1, "Récupération", 0.0, 0.6),
    (2, "Endurance", 0.6, 0.7),
    (3, "Tempo", 0.7, 0.8),
    (4, "Seuil", 0.8, 0.9),
    (5, "Maximal", 0.9, None),
)


@dataclass(frozen=True, slots=True)
class HrZoneBoundary:
    zone: int
    label: str
    lower_bpm: int
    upper_bpm: int | None


def hr_zone_boundaries(max_hr: int) -> list[HrZoneBoundary]:
    boundaries: list[HrZoneBoundary] = []
    for zone, label, lower_pct, upper_pct in _ZONE_DEFINITIONS:
        lower_bpm = round(lower_pct * max_hr)
        upper_bpm = round(upper_pct * max_hr) if upper_pct is not None else None
        boundaries.append(HrZoneBoundary(zone, label, lower_bpm, upper_bpm))
    return boundaries


def _zone_for(hr: int, boundaries: list[HrZoneBoundary]) -> int:
    for boundary in boundaries:
        if hr >= boundary.lower_bpm and (
            boundary.upper_bpm is None or hr < boundary.upper_bpm
        ):
            return boundary.zone
    return boundaries[0].zone


@dataclass(frozen=True, slots=True)
class HrZoneTime:
    zone: int
    label: str
    seconds: float


def compute_hr_zone_times(
    samples: Sequence[tuple[datetime, int | None]], *, max_hr: int
) -> list[HrZoneTime]:
    boundaries = hr_zone_boundaries(max_hr)
    seconds_by_zone = {b.zone: 0.0 for b in boundaries}

    valid = sorted((sample for sample in samples if sample[1] is not None), key=lambda sample: sample[0])
    for (at0, hr0), (at1, _hr1) in zip(valid, valid[1:]):
        elapsed = (at1 - at0).total_seconds()
        if elapsed <= 0:
            continue
        seconds_by_zone[_zone_for(hr0, boundaries)] += elapsed

    return [
        HrZoneTime(zone=b.zone, label=b.label, seconds=seconds_by_zone[b.zone])
        for b in boundaries
    ]
