"""Tests du mapping des mesures corporelles."""

from datetime import datetime, timedelta, timezone

from app.ingestion.samsung.mapper import map_body_measurement

FULL_ROW = {
    "datauuid": "f631923e-bc08-404a-8d0c-9468aa4dee2b",
    "start_time": "2026-08-31 06:29:10.346",
    "time_offset": "UTC+0200",
    "weight": "65.6",
    "body_fat": "10.8",
    "body_fat_mass": "7.0848002",
    "skeletal_muscle_mass": "37.7",
    "skeletal_muscle": "45.72513",
    "fat_free_mass": "57.272385",
    "fat_free": "84.10042",
    "total_body_water": "42.833126",
    "basal_metabolic_rate": "1633",
    "height": "180.0",
}

SPARSE_ROW = {
    "datauuid": "a04ec306-ed98-460e-853f-629b404d0757",
    "start_time": "2018-11-29 22:54:00.000",
    "time_offset": "UTC+0100",
    "weight": "90.0",
    "body_fat": "",
    "body_fat_mass": "",
    "skeletal_muscle_mass": "",
    "skeletal_muscle": "",
    "fat_free_mass": "",
    "fat_free": "",
    "total_body_water": "",
    "basal_metabolic_rate": "",
    "height": "180.0",
}


def test_maps_every_metric() -> None:
    record = map_body_measurement(FULL_ROW)

    assert record is not None
    assert record.source_uuid == "f631923e-bc08-404a-8d0c-9468aa4dee2b"
    assert record.measured_at == datetime(
        2026, 8, 31, 6, 29, 10, tzinfo=timezone(timedelta(hours=2))
    )
    assert record.weight_kg == 65.6
    assert record.body_fat_pct == 10.8
    assert record.body_fat_mass_kg == 7.0848002
    assert record.skeletal_muscle_mass_kg == 37.7
    assert record.skeletal_muscle_pct == 45.72513
    assert record.fat_free_mass_kg == 57.272385
    assert record.fat_free_pct == 84.10042
    assert record.total_body_water_kg == 42.833126
    assert record.basal_metabolic_rate_kcal == 1633
    assert record.height_cm == 180.0


def test_missing_metrics_stay_none() -> None:
    """260 mesures réelles antérieures à 2024 n'ont ni masse grasse ni
    muscle. Les remplacer par 0 ferait plonger les courbes."""
    record = map_body_measurement(SPARSE_ROW)

    assert record is not None
    assert record.weight_kg == 90.0
    assert record.body_fat_pct is None
    assert record.skeletal_muscle_mass_kg is None
    assert record.basal_metabolic_rate_kcal is None


def test_row_without_uuid_is_rejected() -> None:
    """Sans source_uuid, l'idempotence du ré-import est impossible."""
    assert map_body_measurement({**FULL_ROW, "datauuid": ""}) is None


def test_row_with_unreadable_date_is_rejected() -> None:
    assert map_body_measurement({**FULL_ROW, "start_time": "n/a"}) is None
