"""SWOLF agrégé par type de nage."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

UNKNOWN_STROKE = "Inconnu"


@dataclass(frozen=True, slots=True)
class SwimLengthInput:
    idx: int
    duration_ms: int | None
    stroke_count: int | None
    stroke_type: str | None


@dataclass(frozen=True, slots=True)
class SwolfByStroke:
    stroke_type: str
    length_count: int
    mean_swolf: float | None
    mean_duration_s: float | None


def compute_swolf(lengths: Sequence[SwimLengthInput]) -> list[SwolfByStroke]:
    swolf_by_stroke: dict[str, list[float]] = defaultdict(list)
    duration_by_stroke: dict[str, list[float]] = defaultdict(list)

    for length in lengths:
        if length.duration_ms is None or length.stroke_count is None:
            continue
        stroke = length.stroke_type or UNKNOWN_STROKE
        duration_s = length.duration_ms / 1000
        swolf_by_stroke[stroke].append(duration_s + length.stroke_count)
        duration_by_stroke[stroke].append(duration_s)

    return [
        SwolfByStroke(
            stroke_type=stroke,
            length_count=len(values),
            mean_swolf=sum(values) / len(values),
            mean_duration_s=sum(duration_by_stroke[stroke])
            / len(duration_by_stroke[stroke]),
        )
        for stroke, values in swolf_by_stroke.items()
    ]
