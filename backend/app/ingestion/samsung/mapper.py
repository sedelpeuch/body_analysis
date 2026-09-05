"""Transformation des lignes brutes de l'export en dataclasses de domaine.

Ce module est le seul à connaître les noms de colonnes de Samsung Health.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.ingestion.samsung.parsers import (
    parse_aware_datetime,
    parse_float,
    parse_int,
)
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
    StrengthSetRecord,
    WorkoutRecord,
)
from app.ingestion.samsung.sports import resolve_sport

EXERCISE_PREFIX = "com.samsung.health.exercise."

# Sports dont subset_data porte de vraies séries de charge. Les séances de
# natation ont aussi des reps, mais elles comptent des longueurs.
STRENGTH_SPORTS = frozenset({"Musculation", "Poids du corps"})


def map_body_measurement(row: dict[str, str]) -> BodyMeasurementRecord | None:
    """Renvoie None si la ligne n'est pas exploitable.

    Une ligne sans identifiant source ne peut pas être réingérée sans
    doublon ; une ligne sans date n'est situable sur aucune courbe.
    """
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    measured_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if measured_at is None:
        return None
    return BodyMeasurementRecord(
        source_uuid=source_uuid,
        measured_at=measured_at,
        weight_kg=parse_float(row.get("weight")),
        body_fat_pct=parse_float(row.get("body_fat")),
        body_fat_mass_kg=parse_float(row.get("body_fat_mass")),
        skeletal_muscle_mass_kg=parse_float(row.get("skeletal_muscle_mass")),
        skeletal_muscle_pct=parse_float(row.get("skeletal_muscle")),
        fat_free_mass_kg=parse_float(row.get("fat_free_mass")),
        fat_free_pct=parse_float(row.get("fat_free")),
        total_body_water_kg=parse_float(row.get("total_body_water")),
        basal_metabolic_rate_kcal=parse_int(row.get("basal_metabolic_rate")),
        height_cm=parse_float(row.get("height")),
    )


def map_nutrition_entry(row: dict[str, str]) -> NutritionEntryRecord | None:
    """Renvoie None si la ligne n'est pas exploitable (cf. map_body_measurement)."""
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    consumed_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if consumed_at is None:
        return None
    return NutritionEntryRecord(
        source_uuid=source_uuid,
        consumed_at=consumed_at,
        food_name=(row.get("name") or "").strip(),
        meal_type=parse_int(row.get("meal_type")),
        amount=parse_float(row.get("amount")),
        unit_code=parse_int(row.get("unit")),
        calories=parse_float(row.get("calorie")),
    )


@dataclass(frozen=True, slots=True)
class JsonReferences:
    """Noms des fichiers JSON annexes référencés par une ligne de séance."""

    live_data: str | None = None
    location_data: str | None = None
    additional: str | None = None
    sensing_status: str | None = None


def _exercise(row: dict[str, str], name: str) -> str | None:
    return row.get(f"{EXERCISE_PREFIX}{name}")


def _subset_items(row: dict[str, str]) -> list[dict[str, object]]:
    raw = (row.get("subset_data") or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def has_sets(row: dict[str, str]) -> bool:
    return any("reps" in item for item in _subset_items(row))


def map_workout(row: dict[str, str]) -> WorkoutRecord | None:
    """Renvoie None si la ligne n'est pas exploitable (cf. map_body_measurement).

    Le code d'exercice fait foi pour déterminer le sport ; la présence de
    séries (has_sets) ne sert qu'à lever l'ambiguïté du code personnalisé.
    Tester les reps avant le code a autrefois classé 69 séances de natation
    réelles comme de la musculation.
    """
    source_uuid = (_exercise(row, "datauuid") or "").strip()
    if not source_uuid:
        return None
    offset = _exercise(row, "time_offset")
    started_at = parse_aware_datetime(_exercise(row, "start_time"), offset)
    if started_at is None:
        return None
    sport_type = parse_int(_exercise(row, "exercise_type"))
    return WorkoutRecord(
        source_uuid=source_uuid,
        started_at=started_at,
        source_updated_at=parse_aware_datetime(_exercise(row, "update_time"), offset),
        ended_at=parse_aware_datetime(_exercise(row, "end_time"), offset),
        duration_ms=parse_int(_exercise(row, "duration")),
        sport_type=sport_type,
        sport=resolve_sport(sport_type, has_sets=has_sets(row)),
        distance_m=parse_float(_exercise(row, "distance")),
        calories_kcal=parse_float(_exercise(row, "calorie")),
        mean_heart_rate=parse_float(_exercise(row, "mean_heart_rate")),
        max_heart_rate=parse_float(_exercise(row, "max_heart_rate")),
        min_heart_rate=parse_float(_exercise(row, "min_heart_rate")),
        mean_speed_mps=parse_float(_exercise(row, "mean_speed")),
        max_speed_mps=parse_float(_exercise(row, "max_speed")),
        mean_cadence=parse_float(_exercise(row, "mean_cadence")),
        max_cadence=parse_float(_exercise(row, "max_cadence")),
        min_altitude_m=parse_float(_exercise(row, "min_altitude")),
        max_altitude_m=parse_float(_exercise(row, "max_altitude")),
        altitude_gain_m=parse_float(_exercise(row, "altitude_gain")),
        altitude_loss_m=parse_float(_exercise(row, "altitude_loss")),
        start_latitude=parse_float(row.get("start_latitude")),
        start_longitude=parse_float(row.get("start_longitude")),
        vo2_max=parse_float(_exercise(row, "vo2_max")),
        sweat_loss_ml=parse_float(_exercise(row, "sweat_loss")),
    )


def map_strength_sets(row: dict[str, str], sport: str) -> list[StrengthSetRecord]:
    """Ne renvoie des séries que pour les sports de charge.

    Les séances de natation portent aussi des reps dans subset_data (une
    longueur), mais ce ne sont pas des séries de musculation.
    """
    if sport not in STRENGTH_SPORTS:
        return []
    return [
        StrengthSetRecord(
            idx=index,
            duration_s=parse_float(item.get("duration")),
            reps=parse_int(item.get("reps")),
            weight_kg=parse_float(item.get("weight")),
            weight_unit=(
                str(item["weight_unit"]) if item.get("weight_unit") else None
            ),
        )
        for index, item in enumerate(_subset_items(row))
        if "reps" in item
    ]


def _reference(raw: str | None) -> str | None:
    text = (raw or "").strip()
    return text or None


def map_json_references(row: dict[str, str]) -> JsonReferences:
    return JsonReferences(
        live_data=_reference(_exercise(row, "live_data")),
        location_data=_reference(_exercise(row, "location_data")),
        additional=_reference(_exercise(row, "additional")),
        sensing_status=_reference(row.get("sensing_status")),
    )
