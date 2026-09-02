"""Mapping de l'activité et des pas quotidiens."""

from __future__ import annotations

from datetime import date

from app.ingestion.samsung.energy import parse_local_day
from app.ingestion.samsung.records import DailyActivityRecord, StepDailyTrendRecord


def _day_from_row(row: dict[str, str]) -> date | None:
    return parse_local_day(row.get("day_time"))


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
        step_count=int(row.get("step_count"))
        if row.get("step_count") not in (None, "")
        else None,
        active_time_ms=int(row.get("active_time"))
        if row.get("active_time") not in (None, "")
        else None,
        calorie=float(row.get("calorie"))
        if row.get("calorie") not in (None, "")
        else None,
        distance_m=float(row.get("distance"))
        if row.get("distance") not in (None, "")
        else None,
        floor_count=int(row.get("floor_count"))
        if row.get("floor_count") not in (None, "")
        else None,
        score=int(row.get("score")) if row.get("score") not in (None, "") else None,
        exercise_time_ms=int(row.get("exercise_time"))
        if row.get("exercise_time") not in (None, "")
        else None,
        run_time_ms=int(row.get("run_time"))
        if row.get("run_time") not in (None, "")
        else None,
        walk_time_ms=int(row.get("walk_time"))
        if row.get("walk_time") not in (None, "")
        else None,
        longest_active_time_ms=int(row.get("longest_active_time"))
        if row.get("longest_active_time") not in (None, "")
        else None,
        move_hourly_count=int(row.get("move_hourly_count"))
        if row.get("move_hourly_count") not in (None, "")
        else None,
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
        count=int(row.get("count")) if row.get("count") not in (None, "") else None,
        distance_m=float(row.get("distance"))
        if row.get("distance") not in (None, "")
        else None,
        calorie=float(row.get("calorie"))
        if row.get("calorie") not in (None, "")
        else None,
        speed=float(row.get("speed")) if row.get("speed") not in (None, "") else None,
        source_type=int(row.get("source_type"))
        if row.get("source_type") not in (None, "")
        else None,
    )
