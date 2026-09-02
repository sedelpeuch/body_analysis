"""Mappage des signaux continus et nocturnes Samsung Health.

Les relevés IVR/HRV/stress portent leurs agrégats dans la ligne CSV et les
JSON annexes sont utilisés uniquement pour la famille HRV.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.samsung.parsers import (
    parse_aware_datetime,
    parse_float,
    parse_int,
)
from app.ingestion.samsung.records import (
    HeartRateReadingRecord,
    HrvReadingRecord,
    OxygenSaturationReadingRecord,
    RespiratoryRateReadingRecord,
    SkinTemperatureReadingRecord,
    StressReadingRecord,
)


def _iter_numeric_values(payload: object) -> list[float]:
    values: list[float] = []
    if isinstance(payload, list):
        for item in payload:
            values.extend(_iter_numeric_values(item))
        return values
    if isinstance(payload, dict):
        for key in (
            "sdnn",
            "rmssd",
            "value",
            "average",
            "spo2",
            "temperature",
            "score",
            "heart_rate",
        ):
            if key in payload:
                value = parse_float(payload[key])
                if value is not None:
                    values.append(value)
        for nested in payload.values():
            values.extend(_iter_numeric_values(nested))
    elif isinstance(payload, (int, float)):
        values.append(float(payload))
    return values


def _read_binning_file(base_dir: Path, filename: str | None) -> object | None:
    name = (filename or "").strip()
    if not name:
        return None
    path = base_dir / name
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return None


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def map_hrv_reading(row: dict[str, str], base_dir: Path) -> HrvReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get("time_offset")
    started_at = parse_aware_datetime(row.get("start_time"), offset)
    if started_at is None:
        return None
    payload = _read_binning_file(base_dir, row.get("binning_data"))
    values_sdnn = []
    values_rmssd = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                sdnn = parse_float(item.get("sdnn"))
                rmssd = parse_float(item.get("rmssd"))
                if sdnn is not None:
                    values_sdnn.append(sdnn)
                if rmssd is not None:
                    values_rmssd.append(rmssd)
    elif isinstance(payload, dict):
        for key in ("sdnn", "rmssd"):
            value = parse_float(payload.get(key))
            if value is not None and key == "sdnn":
                values_sdnn.append(value)
            if value is not None and key == "rmssd":
                values_rmssd.append(value)
    if not values_sdnn and not values_rmssd:
        # Les entrées sans binning ne sont pas rejetées : on conserve le
        # relevé et ses colonnes nulles, mais il ne doit pas être perdu.
        values_sdnn = [
            parse_float(value)
            for value in _iter_numeric_values(payload)
            if parse_float(value) is not None
        ]
        values_rmssd = values_sdnn[:]
    return HrvReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), offset),
        avg_sdnn=_mean(values_sdnn),
        avg_rmssd=_mean(values_rmssd),
        sample_count=max(len(values_sdnn), len(values_rmssd)),
    )


def map_heart_rate_reading(row: dict[str, str]) -> HeartRateReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get("time_offset")
    started_at = parse_aware_datetime(row.get("start_time"), offset)
    if started_at is None:
        return None
    return HeartRateReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), offset),
        mean_heart_rate=parse_float(row.get("heart_rate")),
        min_heart_rate=parse_float(row.get("min")),
        max_heart_rate=parse_float(row.get("max")),
        heart_beat_count=parse_int(row.get("heart_beat_count")),
        tag_id=parse_int(row.get("tag_id")),
    )


def map_stress_reading(row: dict[str, str]) -> StressReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get("time_offset")
    started_at = parse_aware_datetime(row.get("start_time"), offset)
    if started_at is None:
        return None
    return StressReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), offset),
        score=parse_float(row.get("score")),
        min_score=parse_float(row.get("min")),
        max_score=parse_float(row.get("max")),
        tag_id=parse_int(row.get("tag_id")),
    )


def map_respiratory_rate_reading(
    row: dict[str, str],
) -> RespiratoryRateReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get("time_offset")
    started_at = parse_aware_datetime(row.get("start_time"), offset)
    if started_at is None:
        return None
    return RespiratoryRateReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), offset),
        average=parse_float(row.get("average")),
        lower_limit=parse_float(row.get("lower_limit")),
        upper_limit=parse_float(row.get("upper_limit")),
    )


def map_skin_temperature_reading(
    row: dict[str, str],
) -> SkinTemperatureReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get("time_offset")
    started_at = parse_aware_datetime(row.get("start_time"), offset)
    if started_at is None:
        return None
    return SkinTemperatureReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), offset),
        temperature=parse_float(row.get("temperature")),
        min_temperature=parse_float(row.get("min")),
        max_temperature=parse_float(row.get("max")),
        baseline=parse_float(row.get("baseline")),
    )


def map_oxygen_saturation_reading(
    row: dict[str, str],
) -> OxygenSaturationReadingRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = row.get("time_offset")
    started_at = parse_aware_datetime(row.get("start_time"), offset)
    if started_at is None:
        return None
    return OxygenSaturationReadingRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        ended_at=parse_aware_datetime(row.get("end_time"), offset),
        spo2=parse_float(row.get("spo2")),
        heart_rate=parse_float(row.get("heart_rate")),
        tag_id=parse_int(row.get("tag_id")),
    )
