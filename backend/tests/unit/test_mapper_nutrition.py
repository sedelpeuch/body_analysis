"""Tests du mapping du journal alimentaire."""

from datetime import datetime, timedelta, timezone

from app.ingestion.samsung.mapper import map_nutrition_entry

ROW = {
    "datauuid": "18b7fde3-ec6e-40d7-b9c4-a55bdcbedb10",
    "start_time": "2024-08-14 11:56:40.973",
    "time_offset": "UTC+0200",
    "name": "Gazpacho(Alvalle)",
    "meal_type": "100002",
    "amount": "333.0",
    "unit": "120005",
    "calorie": "134.865",
}


def test_maps_all_fields() -> None:
    record = map_nutrition_entry(ROW)

    assert record is not None
    assert record.source_uuid == "18b7fde3-ec6e-40d7-b9c4-a55bdcbedb10"
    assert record.consumed_at == datetime(
        2024, 8, 14, 11, 56, 40, tzinfo=timezone(timedelta(hours=2))
    )
    assert record.food_name == "Gazpacho(Alvalle)"
    assert record.meal_type == 100002
    assert record.amount == 333.0
    assert record.unit_code == 120005
    assert record.calories == 134.865


def test_food_name_is_stripped_and_defaults_to_empty() -> None:
    assert map_nutrition_entry({**ROW, "name": "  Oeuf  "}).food_name == "Oeuf"
    assert map_nutrition_entry({**ROW, "name": ""}).food_name == ""


def test_negative_unit_code_is_kept() -> None:
    """33 entrées réelles portent l'unité -1. C'est une valeur, pas une
    absence : on la conserve telle quelle plutôt que de la masquer."""
    assert map_nutrition_entry({**ROW, "unit": "-1"}).unit_code == -1


def test_missing_calories_stay_none() -> None:
    assert map_nutrition_entry({**ROW, "calorie": ""}).calories is None


def test_row_without_uuid_or_date_is_rejected() -> None:
    assert map_nutrition_entry({**ROW, "datauuid": ""}) is None
    assert map_nutrition_entry({**ROW, "start_time": ""}) is None
