"""Mapping du sommeil : résumé de nuit (préfixé) et phases (non préfixées).

sleep_stage.sleep_id n'est volontairement pas vérifié contre sleep.csv :
7 segments réels référencent une nuit absente de l'export, et la contrainte
d'unicité de sleep_stage ne doit jamais dépendre de l'ordre d'ingestion des
deux fichiers.
"""

from __future__ import annotations

from app.ingestion.samsung.parsers import parse_aware_datetime, parse_float, parse_int
from app.ingestion.samsung.records import SleepSessionRecord, SleepStageRecord

PREFIX = "com.samsung.health.sleep."


def _prefixed(row: dict[str, str], name: str) -> str | None:
    return row.get(f"{PREFIX}{name}")


def map_sleep_session(row: dict[str, str]) -> SleepSessionRecord | None:
    source_uuid = (_prefixed(row, "datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = _prefixed(row, "time_offset")
    started_at = parse_aware_datetime(_prefixed(row, "start_time"), offset)
    if started_at is None:
        return None
    return SleepSessionRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(_prefixed(row, "end_time"), offset),
        original_wake_up_time=parse_aware_datetime(
            row.get("original_wake_up_time"),
            offset,
        ),
        efficiency=parse_float(row.get("efficiency")),
        efficiency_with_latency=parse_float(row.get("sleep_efficiency_with_latency")),
        physical_recovery=parse_int(row.get("physical_recovery")),
        mental_recovery=parse_int(row.get("mental_recovery")),
        deep_score=parse_int(row.get("deep_score")),
        rem_score=parse_int(row.get("rem_score")),
        wake_score=parse_int(row.get("wake_score")),
        nap_score=parse_int(row.get("nap_score")),
        latency_score=parse_int(row.get("latency_score")),
        sleep_latency=parse_int(row.get("sleep_latency")),
        total_rem_duration=parse_int(row.get("total_rem_duration")),
        total_light_duration=parse_int(row.get("total_light_duration")),
        sleep_duration=parse_int(row.get("sleep_duration")),
        sleep_score=parse_int(row.get("sleep_score")),
        has_sleep_data=parse_int(row.get("has_sleep_data")),
        sleep_type=parse_int(row.get("sleep_type")),
    )


def map_sleep_stage(row: dict[str, str]) -> SleepStageRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    started_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if started_at is None:
        return None
    return SleepStageRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        sleep_source_uuid=(row.get("sleep_id") or "").strip() or None,
        ended_at=parse_aware_datetime(row.get("end_time"), row.get("time_offset")),
        stage=parse_int(row.get("stage")),
    )
