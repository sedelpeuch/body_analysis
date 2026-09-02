"""Tests de la fenêtre alimentaire et des aliments récurrents — spec 5.6."""

from datetime import datetime, timezone

import pytest

from app.analytics.nutrition import NutritionEntryInput, compute_eating_window, compute_top_foods


def test_compute_eating_window_buckets_by_local_hour() -> None:
    entries = [
        NutritionEntryInput(
            consumed_at=datetime(2026, 7, 1, 6, 0, tzinfo=timezone.utc),
            food_name="Avoine",
            calories=350.0,
        ),
        NutritionEntryInput(
            consumed_at=datetime(2026, 7, 1, 6, 30, tzinfo=timezone.utc),
            food_name="Café",
            calories=5.0,
        ),
    ]

    buckets = {b.hour: b for b in compute_eating_window(entries)}

    assert buckets[8].entry_count == 2
    assert buckets[8].total_calories == pytest.approx(355.0)
    assert len(buckets) == 24


def test_compute_eating_window_on_empty_entries_still_returns_24_buckets() -> None:
    buckets = compute_eating_window([])

    assert len(buckets) == 24
    assert all(b.entry_count == 0 and b.total_calories is None for b in buckets)


def test_compute_top_foods_ranks_by_frequency() -> None:
    entries = [
        NutritionEntryInput(datetime(2026, 1, 1, tzinfo=timezone.utc), "Poulet", 200.0),
        NutritionEntryInput(datetime(2026, 1, 2, tzinfo=timezone.utc), "Poulet", 210.0),
        NutritionEntryInput(datetime(2026, 1, 3, tzinfo=timezone.utc), "Riz", 180.0),
    ]

    top = compute_top_foods(entries, limit=10)

    assert top[0].food_name == "Poulet"
    assert top[0].entry_count == 2
    assert top[0].total_calories == pytest.approx(410.0)
    assert top[1].food_name == "Riz"


def test_compute_top_foods_respects_limit() -> None:
    entries = [
        NutritionEntryInput(datetime(2026, 1, i + 1, tzinfo=timezone.utc), f"Aliment {i}", 100.0)
        for i in range(5)
    ]

    top = compute_top_foods(entries, limit=2)

    assert len(top) == 2
