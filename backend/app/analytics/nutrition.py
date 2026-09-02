"""Fenêtre alimentaire et aliments récurrents."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class NutritionEntryInput:
    consumed_at: datetime
    food_name: str
    calories: float | None


@dataclass(frozen=True, slots=True)
class HourlyBucket:
    hour: int
    entry_count: int
    total_calories: float | None


def compute_eating_window(
    entries: Sequence[NutritionEntryInput], *, tz: str = "Europe/Paris"
) -> list[HourlyBucket]:
    zone = ZoneInfo(tz)
    counts = [0] * 24
    totals: list[float | None] = [None] * 24

    for entry in entries:
        hour = entry.consumed_at.astimezone(zone).hour
        counts[hour] += 1
        if entry.calories is not None:
            totals[hour] = (totals[hour] or 0.0) + entry.calories

    return [
        HourlyBucket(hour=h, entry_count=counts[h], total_calories=totals[h])
        for h in range(24)
    ]


@dataclass(frozen=True, slots=True)
class TopFood:
    food_name: str
    entry_count: int
    total_calories: float | None


def compute_top_foods(
    entries: Sequence[NutritionEntryInput], *, limit: int = 10
) -> list[TopFood]:
    counts: Counter[str] = Counter()
    totals: dict[str, float] = defaultdict(float)
    has_calories: dict[str, bool] = defaultdict(bool)

    for entry in entries:
        counts[entry.food_name] += 1
        if entry.calories is not None:
            totals[entry.food_name] += entry.calories
            has_calories[entry.food_name] = True

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [
        TopFood(
            food_name=name,
            entry_count=count,
            total_calories=totals[name] if has_calories[name] else None,
        )
        for name, count in ranked[:limit]
    ]
