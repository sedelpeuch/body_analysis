"""Mapping de la décomposition quotidienne de la dépense énergétique.

com.samsung.shealth.calories_burned.details ne porte pas de colonne time_
offset : day_time est une minuit locale sans fuseau exploitable. On n'en
retient que la date, jamais un TIMESTAMPTZ inventé.
"""

from __future__ import annotations

from datetime import date

from app.ingestion.samsung.parsers import _DATETIME_RE, parse_float, parse_int
from app.ingestion.samsung.records import EnergyExpenditureRecord

PREFIX = "com.samsung.shealth.calories_burned."


def parse_local_day(raw: object) -> date | None:
    text = "" if raw is None else str(raw).strip()
    match = _DATETIME_RE.search(text)
    if match is None:
        return None
    year, month, day = (int(match.group(i)) for i in (1, 2, 3))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _prefixed(row: dict[str, str], name: str) -> str | None:
    return row.get(f"{PREFIX}{name}")


def map_energy_expenditure(row: dict[str, str]) -> EnergyExpenditureRecord | None:
    source_uuid = (_prefixed(row, "datauuid") or "").strip()
    if not source_uuid:
        return None
    day = parse_local_day(_prefixed(row, "day_time"))
    if day is None:
        return None
    return EnergyExpenditureRecord(
        source_uuid=source_uuid,
        day=day,
        rest_calorie=parse_float(_prefixed(row, "rest_calorie")),
        active_calorie=parse_float(_prefixed(row, "active_calorie")),
        tef_calorie=parse_float(_prefixed(row, "tef_calorie")),
        active_time_ms=parse_int(_prefixed(row, "active_time")),
        total_exercise_calories=parse_float(row.get("total_exercise_calories")),
    )
