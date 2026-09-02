"""Tests du mapping des séances."""

import json
from datetime import datetime, timedelta, timezone

from app.ingestion.samsung.mapper import (
    has_sets,
    map_json_references,
    map_strength_sets,
    map_workout,
)

P = "com.samsung.health.exercise."

STRENGTH_SUBSET = json.dumps(
    [
        {"duration": 42, "reps": 10, "weight": 0.0, "weight_unit": "kg"},
        {"duration": 35, "reps": 10, "weight": 20.5, "weight_unit": "kg"},
    ]
)

SWIM_SUBSET = json.dumps(
    [
        {
            "duration": 1800,
            "distance": 0,
            "reps": 20,
            "extra_data": '{"poolLength":1,"poolLengthUnit":"m"}',
        }
    ]
)

RUN_ROW = {
    f"{P}datauuid": "185e928e-af99-46fd-9dad-35f114d5b32d",
    f"{P}start_time": "2026-02-05 19:02:05.000",
    f"{P}end_time": "2026-02-05 19:13:24.000",
    f"{P}time_offset": "UTC+0100",
    f"{P}duration": "678496",
    f"{P}exercise_type": "1002",
    f"{P}distance": "975.32",
    f"{P}calorie": "37.27",
    f"{P}mean_heart_rate": "148.5",
    f"{P}max_heart_rate": "171",
    f"{P}min_heart_rate": "96",
    f"{P}mean_speed": "1.4374734",
    f"{P}max_speed": "1.75",
    f"{P}mean_cadence": "160",
    f"{P}max_cadence": "178",
    f"{P}min_altitude": "12.0",
    f"{P}max_altitude": "48.5",
    f"{P}altitude_gain": "36.5",
    f"{P}altitude_loss": "30.0",
    f"{P}vo2_max": "",
    f"{P}sweat_loss": "",
    f"{P}live_data": (
        "185e928e-af99-46fd-9dad-35f114d5b32d"
        ".com.samsung.health.exercise.live_data.json"
    ),
    f"{P}location_data": "",
    f"{P}additional": "",
    "start_latitude": "44.8010456",
    "start_longitude": "-0.5758588",
    "subset_data": "",
    "sensing_status": "",
}


def test_maps_run_summary() -> None:
    record = map_workout(RUN_ROW)

    assert record is not None
    assert record.source_uuid == "185e928e-af99-46fd-9dad-35f114d5b32d"
    assert record.started_at == datetime(
        2026, 2, 5, 19, 2, 5, tzinfo=timezone(timedelta(hours=1))
    )
    assert record.ended_at == datetime(
        2026, 2, 5, 19, 13, 24, tzinfo=timezone(timedelta(hours=1))
    )
    assert record.duration_ms == 678496
    assert record.sport_type == 1002
    assert record.sport == "Course à pied"
    assert record.distance_m == 975.32
    assert record.calories_kcal == 37.27
    assert record.mean_heart_rate == 148.5
    assert record.max_heart_rate == 171.0
    assert record.min_heart_rate == 96.0
    assert record.mean_speed_mps == 1.4374734
    assert record.altitude_gain_m == 36.5
    assert record.start_latitude == 44.8010456
    assert record.start_longitude == -0.5758588


def test_empty_vo2_and_sweat_stay_none() -> None:
    """Colonnes présentes mais vides dans les données réelles."""
    record = map_workout(RUN_ROW)

    assert record.vo2_max is None
    assert record.sweat_loss_ml is None


def test_swimming_with_sets_is_still_swimming() -> None:
    """Verrou de non-régression du bug corrigé en tâche 3, au niveau du
    mapper cette fois : la séance porte des reps ET le code natation."""
    row = {**RUN_ROW, f"{P}exercise_type": "14001", "subset_data": SWIM_SUBSET}

    assert map_workout(row).sport == "Natation"


def test_custom_code_uses_sets_to_disambiguate() -> None:
    with_sets = {**RUN_ROW, f"{P}exercise_type": "0", "subset_data": STRENGTH_SUBSET}
    without_sets = {**RUN_ROW, f"{P}exercise_type": "0", "subset_data": ""}

    assert map_workout(with_sets).sport == "Musculation"
    assert map_workout(without_sets).sport == "Marche"


def test_has_sets_detects_reps() -> None:
    assert has_sets({"subset_data": STRENGTH_SUBSET}) is True
    assert has_sets({"subset_data": ""}) is False
    assert has_sets({"subset_data": "pas du json"}) is False
    assert has_sets({"subset_data": "[]"}) is False
    assert has_sets({"subset_data": '[{"duration": 42}]'}) is False


def test_maps_strength_sets_for_strength_sports() -> None:
    sets = map_strength_sets({"subset_data": STRENGTH_SUBSET}, "Musculation")

    assert len(sets) == 2
    assert sets[0].idx == 0
    assert sets[0].duration_s == 42.0
    assert sets[0].reps == 10
    assert sets[0].weight_kg == 0.0
    assert sets[0].weight_unit == "kg"
    assert sets[1].idx == 1
    assert sets[1].weight_kg == 20.5


def test_does_not_map_swim_subset_as_strength_sets() -> None:
    """Les reps d'une séance de natation ne sont pas des séries de charge ;
    les stocker comme telles polluerait le volume de musculation."""
    assert map_strength_sets({"subset_data": SWIM_SUBSET}, "Natation") == []


def test_maps_json_references() -> None:
    refs = map_json_references(RUN_ROW)

    assert refs.live_data == (
        "185e928e-af99-46fd-9dad-35f114d5b32d"
        ".com.samsung.health.exercise.live_data.json"
    )
    assert refs.location_data is None
    assert refs.additional is None
    assert refs.sensing_status is None


def test_row_without_uuid_or_date_is_rejected() -> None:
    assert map_workout({**RUN_ROW, f"{P}datauuid": ""}) is None
    assert map_workout({**RUN_ROW, f"{P}start_time": ""}) is None
