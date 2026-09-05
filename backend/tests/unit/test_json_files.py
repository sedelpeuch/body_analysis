"""Tests de la lecture des fichiers JSON annexes de l'export."""

from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.samsung.json_files import (
    load_json,
    map_heart_rate_thresholds,
    map_locations,
    map_pool_length,
    map_samples,
    map_swim_lengths,
    resolve_json_path,
)

EXERCISE_DIR = Path(__file__).parent.parent / "fixtures" / "samsung" / "exercise"

LIVE = (
    "11111111-1111-1111-1111-111111111111"
    ".com.samsung.health.exercise.live_data.json"
)
LOCATION = (
    "22222222-2222-2222-2222-222222222222"
    ".com.samsung.health.exercise.location_data.json"
)
ADDITIONAL = (
    "33333333-3333-3333-3333-333333333333"
    ".com.samsung.health.exercise.additional.json"
)
SENSING = "44444444-4444-4444-4444-444444444444.sensing_status.json"


def test_resolve_json_path_uses_first_character_subdirectory() -> None:
    path = resolve_json_path(EXERCISE_DIR, LIVE)

    assert path is not None
    assert path.parent.name == "1"
    assert path.exists()


def test_resolve_json_path_returns_none_for_missing_or_empty() -> None:
    assert resolve_json_path(EXERCISE_DIR, None) is None
    assert resolve_json_path(EXERCISE_DIR, "") is None
    assert resolve_json_path(EXERCISE_DIR, "nope.json") is None


def test_map_samples_reads_every_metric() -> None:
    """La troisième entrée de la fixture partage l'horodatage de la
    première et la remplace (cf. dédoublonnage ci-dessous) : les valeurs
    attendues ici sont donc celles de la dernière occurrence survivante,
    pas celles de la première entrée du fichier."""
    samples = map_samples(load_json(resolve_json_path(EXERCISE_DIR, LIVE)))

    first = samples[0]
    assert first.at == datetime(2022, 2, 5, 18, 27, tzinfo=UTC)
    assert first.heart_rate == 199
    assert first.speed_mps == 9.9
    assert first.distance_m == 99.9
    assert first.calories_kcal == 9.99
    assert first.cadence is None
    assert first.segment == 1


def test_map_samples_deduplicates_on_timestamp_keeping_last() -> None:
    """La clé primaire est (workout_id, at) ; un doublon ferait échouer
    l'insertion par lot entière."""
    samples = map_samples(load_json(resolve_json_path(EXERCISE_DIR, LIVE)))

    assert len(samples) == 2
    assert [s.at for s in samples] == sorted(s.at for s in samples)
    duplicated = next(
        s for s in samples if s.at == datetime(2022, 2, 5, 18, 27, tzinfo=UTC)
    )
    assert duplicated.heart_rate == 199


def test_map_samples_tolerates_absent_metrics() -> None:
    samples = map_samples(load_json(resolve_json_path(EXERCISE_DIR, LIVE)))
    later = max(samples, key=lambda s: s.at)

    assert later.cadence is None


def test_map_samples_reads_float_typed_json_numbers() -> None:
    """Verrou de non-régression : l'export réel sérialise heart_rate,
    cadence et elapsed_time en float JSON (100.0) sur certains fichiers et
    en int réel sur d'autres, sans cohérence. Un parse_int strict sur ces
    champs laissait heart_rate/elapsed_ms/cadence NULL sur les 2,4 M lignes
    de workout_sample de l'export réel — jamais détecté ici tant que le
    fixture n'utilisait que des entiers JSON."""
    payload = [
        {
            "start_time": 1644085620000,
            "heart_rate": 100.0,
            "cadence": 78.0,
            "elapsed_time": 5000.0,
        },
    ]

    samples = map_samples(payload)

    assert samples[0].heart_rate == 100
    assert samples[0].cadence == 78
    assert samples[0].elapsed_ms == 5000


def test_map_locations_requires_coordinates() -> None:
    """Un point sans latitude n'est pas plaçable ; il est écarté plutôt que
    stocké avec une coordonnée nulle."""
    locations = map_locations(load_json(resolve_json_path(EXERCISE_DIR, LOCATION)))

    assert len(locations) == 2
    assert locations[0].latitude == 44.8010456
    assert locations[0].altitude_m == 16.653
    assert locations[0].accuracy_m == 10.0
    assert locations[1].altitude_m is None


def test_map_swim_lengths() -> None:
    lengths = map_swim_lengths(load_json(resolve_json_path(EXERCISE_DIR, ADDITIONAL)))

    assert len(lengths) == 2
    assert lengths[0].idx == 0
    assert lengths[0].duration_ms == 25379
    assert lengths[0].stroke_count == 8
    assert lengths[0].stroke_type == "Freestyle"
    assert lengths[0].resting_time_ms == 0
    assert lengths[1].stroke_type == "Breaststroke"
    assert lengths[1].resting_time_ms == 1200


def test_map_pool_length() -> None:
    payload = load_json(resolve_json_path(EXERCISE_DIR, ADDITIONAL))

    assert map_pool_length(payload) == 25.0


def test_map_pool_length_ignores_non_metric_units() -> None:
    """Seuls les bassins en mètres sont convertibles sans hypothèse."""
    assert map_pool_length({"pool_length": 25, "pool_length_unit": "yard"}) is None


def test_map_swim_lengths_on_non_swim_payload_is_empty() -> None:
    assert map_swim_lengths({"exercise_type": 1002, "main_workout": {}}) == []


def test_map_heart_rate_thresholds() -> None:
    thresholds = map_heart_rate_thresholds(
        load_json(resolve_json_path(EXERCISE_DIR, SENSING))
    )

    assert thresholds.max_hr_custom == 200
    assert thresholds.max_hr_auto == 188
    assert thresholds.aerobic == 135
    assert thresholds.anaerobic == 166
    assert thresholds.resting == 60


def test_map_heart_rate_thresholds_on_empty_payload() -> None:
    empty = map_heart_rate_thresholds(None)

    assert empty.max_hr_custom is None
    assert empty.resting is None


def test_load_json_returns_none_on_unreadable_file(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{ pas du json", encoding="utf-8")

    assert load_json(broken) is None
