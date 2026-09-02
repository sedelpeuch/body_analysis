"""Transformation des lignes brutes de l'export en dataclasses de domaine.

Ce module est le seul à connaître les noms de colonnes de Samsung Health.
"""

from __future__ import annotations

from app.ingestion.samsung.parsers import (
    parse_aware_datetime,
    parse_float,
    parse_int,
)
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
)


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
