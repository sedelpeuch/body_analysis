"""Résolution et lecture des fichiers JSON annexes de l'export.

L'export place chaque fichier dans un sous-répertoire nommé par le premier
caractère de son nom.

Les fichiers live_data_internal et location_data_internal (224 Mo au total)
ne sont volontairement pas traités : ils ne contiennent que des métadonnées
d'intervalle sans valeur analytique (cf. spec section 7).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.samsung.parsers import (
    parse_epoch_millis,
    parse_float,
    parse_int,
    parse_json_int,
)
from app.ingestion.samsung.records import (
    LocationRecord,
    SampleRecord,
    SwimLengthRecord,
)

METRIC_POOL_UNITS = frozenset({"meter", "meters", "m"})


@dataclass(frozen=True, slots=True)
class HeartRateThresholds:
    max_hr_custom: int | None = None
    max_hr_auto: int | None = None
    aerobic: int | None = None
    anaerobic: int | None = None
    resting: int | None = None


def resolve_json_path(exercise_dir: Path, filename: str | None) -> Path | None:
    name = (filename or "").strip()
    if not name:
        return None
    candidate = exercise_dir / name[0] / name
    return candidate if candidate.is_file() else None


def load_json(path: Path | None) -> object | None:
    if path is None:
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _items(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def map_samples(payload: object) -> list[SampleRecord]:
    """Déduplique sur l'horodatage, la dernière occurrence gagnant.

    La clé primaire est (workout_id, at) ; un doublon ferait échouer tout le
    lot d'insertion.
    """
    by_timestamp: dict[object, SampleRecord] = {}
    for item in _items(payload):
        at = parse_epoch_millis(item.get("start_time"))
        if at is None:
            continue
        by_timestamp[at] = SampleRecord(
            at=at,
            elapsed_ms=parse_json_int(item.get("elapsed_time")),
            heart_rate=parse_json_int(item.get("heart_rate")),
            speed_mps=parse_float(item.get("speed")),
            distance_m=parse_float(item.get("distance")),
            calories_kcal=parse_float(item.get("calorie")),
            cadence=parse_json_int(item.get("cadence")),
            segment=parse_json_int(item.get("segment")),
        )
    return sorted(by_timestamp.values(), key=lambda sample: sample.at)


def map_locations(payload: object) -> list[LocationRecord]:
    by_timestamp: dict[object, LocationRecord] = {}
    for item in _items(payload):
        at = parse_epoch_millis(item.get("start_time"))
        latitude = parse_float(item.get("latitude"))
        longitude = parse_float(item.get("longitude"))
        if at is None or latitude is None or longitude is None:
            continue
        by_timestamp[at] = LocationRecord(
            at=at,
            latitude=latitude,
            longitude=longitude,
            altitude_m=parse_float(item.get("altitude")),
            accuracy_m=parse_float(item.get("accuracy")),
        )
    return sorted(by_timestamp.values(), key=lambda point: point.at)


def map_swim_lengths(payload: object) -> list[SwimLengthRecord]:
    if not isinstance(payload, dict):
        return []
    lengths = payload.get("lengths")
    if not isinstance(lengths, list):
        return []
    records: list[SwimLengthRecord] = []
    for index, item in enumerate(lengths):
        if not isinstance(item, dict):
            continue
        stroke = item.get("stroke_type")
        records.append(
            SwimLengthRecord(
                idx=index,
                duration_ms=parse_int(item.get("duration")),
                stroke_count=parse_int(item.get("stroke_count")),
                stroke_type=str(stroke) if stroke else None,
                resting_time_ms=parse_int(item.get("resting_time")),
            )
        )
    return records


def map_pool_length(payload: object) -> float | None:
    if not isinstance(payload, dict):
        return None
    unit = str(payload.get("pool_length_unit") or "").strip().lower()
    if unit not in METRIC_POOL_UNITS:
        return None
    return parse_float(payload.get("pool_length"))


def map_heart_rate_thresholds(payload: object) -> HeartRateThresholds:
    if not isinstance(payload, dict):
        return HeartRateThresholds()
    heart_rate = payload.get("heart_rate")
    if not isinstance(heart_rate, dict):
        return HeartRateThresholds()
    return HeartRateThresholds(
        max_hr_custom=parse_int(heart_rate.get("max_hr_custom")),
        max_hr_auto=parse_int(heart_rate.get("max_hr_auto")),
        aerobic=parse_int(heart_rate.get("at")),
        anaerobic=parse_int(heart_rate.get("ant")),
        resting=parse_int(heart_rate.get("rhr")),
    )
