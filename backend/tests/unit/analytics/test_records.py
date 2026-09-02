"""Tests des records par sport — le filtrage par sport est fait en amont."""

from datetime import datetime, timezone

from app.analytics.records import WorkoutSummaryInput, compute_records

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 2, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 3, 1, tzinfo=timezone.utc)


def test_compute_records_finds_longest_distance() -> None:
    workouts = [
        WorkoutSummaryInput(1, T0, distance_m=5000.0, duration_ms=1_800_000, calories_kcal=400.0, mean_speed_mps=2.8),
        WorkoutSummaryInput(2, T1, distance_m=10000.0, duration_ms=3_600_000, calories_kcal=750.0, mean_speed_mps=2.8),
    ]

    records = {r.label: r for r in compute_records(workouts)}

    assert records["Distance la plus longue"].workout_id == 2
    assert records["Distance la plus longue"].value == 10000.0


def test_compute_records_finds_longest_duration_and_highest_speed_and_calories() -> None:
    workouts = [
        WorkoutSummaryInput(1, T0, distance_m=5000.0, duration_ms=3_700_000, calories_kcal=900.0, mean_speed_mps=1.5),
        WorkoutSummaryInput(2, T1, distance_m=10000.0, duration_ms=3_600_000, calories_kcal=750.0, mean_speed_mps=3.0),
    ]

    records = {r.label: r for r in compute_records(workouts)}

    assert records["Durée la plus longue"].workout_id == 1
    assert records["Vitesse moyenne la plus élevée"].workout_id == 2
    assert records["Calories les plus élevées"].workout_id == 1


def test_compute_records_ignores_missing_values_per_category() -> None:
    workouts = [
        WorkoutSummaryInput(1, T0, distance_m=None, duration_ms=1_800_000, calories_kcal=400.0, mean_speed_mps=None),
        WorkoutSummaryInput(2, T1, distance_m=8000.0, duration_ms=1_200_000, calories_kcal=300.0, mean_speed_mps=2.5),
    ]

    records = {r.label: r for r in compute_records(workouts)}

    assert records["Distance la plus longue"].workout_id == 2
    assert records["Durée la plus longue"].workout_id == 1


def test_compute_records_on_empty_workouts_returns_empty_list() -> None:
    assert compute_records([]) == []
