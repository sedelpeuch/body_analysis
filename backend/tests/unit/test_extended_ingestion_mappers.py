"""Tests unitaires des mappers d’ingestion étendue."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.ingestion.samsung.activity import map_daily_activity, map_step_daily_trend
from app.ingestion.samsung.energy import map_energy_expenditure, parse_local_day
from app.ingestion.samsung.nutrition_detail import map_nutrition_detail
from app.ingestion.samsung.parsers import read_samsung_csv
from app.ingestion.samsung.sleep import map_sleep_session, map_sleep_stage
from app.ingestion.samsung.vitals import (
    map_heart_rate_reading,
    map_hrv_reading,
    map_stress_reading,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"


def test_maps_nutrition_detail() -> None:
    rows = list(read_samsung_csv(FIXTURES / "nutrition_sample.csv"))
    row = rows[0]

    record = map_nutrition_detail(row)

    assert record is not None
    assert record.source_uuid == "cc453be7-2248-423a-a4a9-3b7e2380a4d7"
    assert record.consumed_at == datetime(
        2024,
        8,
        14,
        15,
        35,
        32,
        tzinfo=timezone(timedelta(hours=2)),
    )
    assert record.protein == 24.4
    assert record.carbohydrate == 46.2


def test_maps_energy_expenditure() -> None:
    rows = list(read_samsung_csv(FIXTURES / "calories_burned_sample.csv"))
    row = rows[0]

    record = map_energy_expenditure(row)

    assert record is not None
    assert record.source_uuid == "ebd0e5f6-7016-4446-b8a0-d57584762484"
    assert record.day == date(2018, 11, 28)
    assert record.active_time_ms == 1632770


def test_parse_local_day_handles_date_strings() -> None:
    assert parse_local_day("2018-11-28 00:00:00.000") == date(2018, 11, 28)
    assert parse_local_day("") is None


def test_maps_sleep_session_and_stage() -> None:
    sleep_rows = list(read_samsung_csv(FIXTURES / "sleep_sample.csv"))
    stage_rows = list(read_samsung_csv(FIXTURES / "sleep_stage_sample.csv"))

    sleep = map_sleep_session(sleep_rows[0])
    stage = map_sleep_stage(stage_rows[0])

    assert sleep is not None
    assert sleep.source_uuid == "2ca56115-6553-45f1-bfa7-eb37c4c77ac9"
    assert sleep.started_at == datetime(
        2024,
        12,
        22,
        23,
        0,
        tzinfo=timezone(timedelta(hours=1)),
    )
    assert stage is not None
    assert stage.source_uuid == "27c5a75c-cc02-49c1-9a01-084e1e0cbd65"
    assert stage.sleep_source_uuid == "2ca56115-6553-45f1-bfa7-eb37c4c77ac9"


def test_maps_vitals_and_activity() -> None:
    hrv_row = next(iter(read_samsung_csv(FIXTURES / "hrv_sample.csv")))
    hr_row = next(iter(read_samsung_csv(FIXTURES / "heart_rate_sample.csv")))
    stress_row = next(iter(read_samsung_csv(FIXTURES / "stress_sample.csv")))
    activity_row = next(iter(read_samsung_csv(FIXTURES / "day_summary_sample.csv")))
    steps_row = next(iter(read_samsung_csv(FIXTURES / "step_daily_trend_sample.csv")))

    hrv = map_hrv_reading(hrv_row, FIXTURES / "hrv")
    heart = map_heart_rate_reading(hr_row)
    stress = map_stress_reading(stress_row)
    activity = map_daily_activity(activity_row)
    steps = map_step_daily_trend(steps_row)

    assert hrv is not None and hrv.sample_count == 2
    assert heart is not None and heart.mean_heart_rate == 80.0
    assert stress is not None and stress.score == 44.0
    assert activity is not None and activity.day == date(2018, 11, 28)
    assert steps is not None and steps.count == 2803
