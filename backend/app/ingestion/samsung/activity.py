"""Mapping de l'activité et des pas quotidiens."""

from __future__ import annotations

from datetime import date

from app.ingestion.samsung.energy import parse_local_day
from app.ingestion.samsung.parsers import parse_float
from app.ingestion.samsung.records import DailyActivityRecord, StepDailyTrendRecord


def _day_from_row(row: dict[str, str]) -> date | None:
    return parse_local_day(row.get("day_time"))


def _int(raw: str | None) -> int | None:
    """Certains compteurs entiers (ex. floor_count) sont sérialisés en
    notation flottante ("0.0") dans l'export : int() seul lève ValueError."""
    value = parse_float(raw)
    return None if value is None else int(value)


def map_daily_activity(row: dict[str, str]) -> DailyActivityRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    day = _day_from_row(row)
    if day is None:
        return None
    return DailyActivityRecord(
        source_uuid=source_uuid,
        day=day,
        step_count=_int(row.get("step_count")),
        active_time_ms=_int(row.get("active_time")),
        calorie=parse_float(row.get("calorie")),
        distance_m=parse_float(row.get("distance")),
        floor_count=_int(row.get("floor_count")),
        score=_int(row.get("score")),
        exercise_time_ms=_int(row.get("exercise_time")),
        run_time_ms=_int(row.get("run_time")),
        walk_time_ms=_int(row.get("walk_time")),
        longest_active_time_ms=_int(row.get("longest_active_time")),
        move_hourly_count=_int(row.get("move_hourly_count")),
    )


def map_step_daily_trend(row: dict[str, str]) -> StepDailyTrendRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    day = _day_from_row(row)
    if day is None:
        return None
    return StepDailyTrendRecord(
        source_uuid=source_uuid,
        day=day,
        count=_int(row.get("count")),
        distance_m=parse_float(row.get("distance")),
        calorie=parse_float(row.get("calorie")),
        speed=parse_float(row.get("speed")),
        source_type=_int(row.get("source_type")),
    )
