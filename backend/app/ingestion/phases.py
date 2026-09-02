"""Lecture du fichier phases.json de l'application Streamlit."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.ingestion.samsung.parsers import parse_float, parse_int
from app.ingestion.samsung.records import PhaseRecord

VALID_KINDS = frozenset({"free", "bulk", "cut", "maintain"})
DEFAULT_KIND = "free"


def _parse_date(raw: object) -> date | None:
    try:
        return date.fromisoformat(str(raw).strip())
    except (TypeError, ValueError):
        return None


def read_phases(path: Path) -> list[PhaseRecord]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return []
    if not isinstance(payload, list):
        return []

    records: list[PhaseRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        starts_on = _parse_date(item.get("start"))
        ends_on = _parse_date(item.get("end"))
        if starts_on is None or ends_on is None or ends_on < starts_on:
            continue
        kind = str(item.get("type") or "").strip().lower()
        objectives = item.get("objectives")
        objectives = objectives if isinstance(objectives, dict) else {}
        records.append(
            PhaseRecord(
                name=str(item.get("name") or "").strip(),
                kind=kind if kind in VALID_KINDS else DEFAULT_KIND,
                starts_on=starts_on,
                ends_on=ends_on,
                weight_target_kg=parse_float(objectives.get("weight_target")),
                body_fat_target_pct=parse_float(objectives.get("body_fat_target")),
                skeletal_muscle_target_kg=parse_float(
                    objectives.get("muscle_target")
                ),
                daily_calories_target=parse_int(objectives.get("calories_target")),
            )
        )
    return sorted(records, key=lambda record: record.starts_on)
