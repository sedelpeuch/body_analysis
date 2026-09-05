"""Mapping des repas de com.samsung.health.nutrition.

Distincte de food_intake (plan 1) : aucune clé commune fiable, cf. plan
« Décisions actées ». Ce module ne connaît que les colonnes de nutrition.csv.
"""

from __future__ import annotations

from app.ingestion.samsung.parsers import parse_aware_datetime, parse_float, parse_int
from app.ingestion.samsung.records import NutritionDetailRecord


def map_nutrition_detail(row: dict[str, str]) -> NutritionDetailRecord | None:
    source_uuid = (row.get("datauuid") or "").strip()
    if not source_uuid:
        return None
    consumed_at = parse_aware_datetime(row.get("start_time"), row.get("time_offset"))
    if consumed_at is None:
        return None
    return NutritionDetailRecord(
        source_uuid=source_uuid,
        consumed_at=consumed_at,
        meal_type=parse_int(row.get("meal_type")),
        title=(row.get("title") or "").strip(),
        calories=parse_float(row.get("calorie")),
        protein=parse_float(row.get("protein")),
        total_fat=parse_float(row.get("total_fat")),
        saturated_fat=parse_float(row.get("saturated_fat")),
        trans_fat=parse_float(row.get("trans_fat")),
        monosaturated_fat=parse_float(row.get("monosaturated_fat")),
        polysaturated_fat=parse_float(row.get("polysaturated_fat")),
        carbohydrate=parse_float(row.get("carbohydrate")),
        dietary_fiber=parse_float(row.get("dietary_fiber")),
        sugar=parse_float(row.get("sugar")),
        added_sugar=parse_float(row.get("added_sugar")),
        cholesterol=parse_float(row.get("cholesterol")),
        sodium=parse_float(row.get("sodium")),
        potassium=parse_float(row.get("potassium")),
        calcium=parse_float(row.get("calcium")),
        iron=parse_float(row.get("iron")),
        vitamin_a=parse_float(row.get("vitamin_a")),
        vitamin_c=parse_float(row.get("vitamin_c")),
        vitamin_d=parse_float(row.get("vitamin_d")),
    )
