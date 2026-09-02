"""Tests de l'assemblage d'une séance et de ses dépendances."""

import json
from pathlib import Path

from app.ingestion.samsung.assembler import build_workout_bundle

EXERCISE_DIR = Path(__file__).parent.parent / "fixtures" / "samsung" / "exercise"
P = "com.samsung.health.exercise."

BASE_ROW = {
    f"{P}datauuid": "185e928e-af99-46fd-9dad-35f114d5b32d",
    f"{P}start_time": "2022-02-05 20:27:00.000",
    f"{P}time_offset": "UTC+0100",
    f"{P}exercise_type": "1002",
    f"{P}live_data": (
        "11111111-1111-1111-1111-111111111111"
        ".com.samsung.health.exercise.live_data.json"
    ),
    f"{P}location_data": (
        "22222222-2222-2222-2222-222222222222"
        ".com.samsung.health.exercise.location_data.json"
    ),
    f"{P}additional": "",
    "sensing_status": "44444444-4444-4444-4444-444444444444.sensing_status.json",
    "subset_data": "",
}

SWIM_ROW = {
    **BASE_ROW,
    f"{P}exercise_type": "14001",
    f"{P}live_data": "",
    f"{P}location_data": "",
    f"{P}additional": (
        "33333333-3333-3333-3333-333333333333"
        ".com.samsung.health.exercise.additional.json"
    ),
    "sensing_status": "",
}


def test_bundles_samples_and_locations() -> None:
    bundle = build_workout_bundle(BASE_ROW, EXERCISE_DIR)

    assert bundle is not None
    assert len(bundle.samples) == 2
    assert len(bundle.locations) == 2


def test_merges_heart_rate_thresholds_into_workout() -> None:
    """Les seuils vivent dans sensing_status, pas dans la ligne CSV."""
    bundle = build_workout_bundle(BASE_ROW, EXERCISE_DIR)

    assert bundle.workout.max_hr_custom == 200
    assert bundle.workout.max_hr_auto == 188
    assert bundle.workout.hr_aerobic_threshold == 135
    assert bundle.workout.hr_anaerobic_threshold == 166
    assert bundle.workout.resting_hr == 60


def test_bundles_swim_lengths_and_pool_length() -> None:
    bundle = build_workout_bundle(SWIM_ROW, EXERCISE_DIR)

    assert bundle.workout.sport == "Natation"
    assert bundle.workout.pool_length_m == 25.0
    assert len(bundle.swim_lengths) == 2
    assert bundle.swim_lengths[0].stroke_type == "Freestyle"


def test_bundles_strength_sets_for_musculation() -> None:
    row = {
        **BASE_ROW,
        f"{P}exercise_type": "10026",
        "subset_data": json.dumps(
            [{"duration": 42, "reps": 10, "weight": 20.0, "weight_unit": "kg"}]
        ),
    }

    bundle = build_workout_bundle(row, EXERCISE_DIR)

    assert bundle.workout.sport == "Musculation"
    assert len(bundle.strength_sets) == 1
    assert bundle.strength_sets[0].reps == 10


def test_keeps_additional_payload_as_extra() -> None:
    bundle = build_workout_bundle(SWIM_ROW, EXERCISE_DIR)

    kinds = {extra.kind for extra in bundle.extras}
    assert "additional" in kinds


def test_missing_json_files_yield_empty_lists() -> None:
    row = {
        **BASE_ROW,
        f"{P}live_data": "absent.json",
        f"{P}location_data": "",
        "sensing_status": "",
    }

    bundle = build_workout_bundle(row, EXERCISE_DIR)

    assert bundle is not None
    assert bundle.samples == []
    assert bundle.locations == []
    assert bundle.workout.resting_hr is None


def test_unmappable_row_yields_none() -> None:
    assert build_workout_bundle({**BASE_ROW, f"{P}datauuid": ""}, EXERCISE_DIR) is None
