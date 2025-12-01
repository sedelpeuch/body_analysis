from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

import csv
import io
import math
import re
import calendar
from datetime import datetime


DATA_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@dataclass
class DataPaths:
    weight_csv: Optional[str]
    food_csv: Optional[str]


def find_data_files(data_dir: Optional[str] = None) -> DataPaths:
    """Locate Samsung Health export CSVs in the given data directory."""
    data_dir = data_dir or DATA_DIR_DEFAULT
    weight_matches = glob.glob(
        os.path.join(data_dir, "com.samsung.health.weight.*.csv")
    )
    food_matches = glob.glob(
        os.path.join(data_dir, "com.samsung.health.food_intake.*.csv")
    )
    return DataPaths(
        weight_csv=weight_matches[0] if weight_matches else None,
        food_csv=food_matches[0] if food_matches else None,
    )


def _parse_datetime_str(s: Optional[str]) -> Optional[datetime]:
    """Parse date string like 'YYYY-MM-DD HH:MM:SS...' into naive datetime.

    Avoid exceptions by validating components before constructing the datetime.
    """
    if s is None:
        return None
    txt = str(s).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})", txt)
    if not m:
        return None
    y = int(m.group(1))
    mo = int(m.group(2))
    d = int(m.group(3))
    h = int(m.group(4))
    mi = int(m.group(5))
    se = int(m.group(6))
    if mo < 1 or mo > 12:
        return None
    max_day = calendar.monthrange(y, mo)[1]
    if d < 1 or d > max_day:
        return None
    if not (0 <= h <= 23 and 0 <= mi <= 59 and 0 <= se <= 59):
        return None
    return datetime(y, mo, d, h, mi, se)


def _to_float(x) -> float:
    s = ("" if x is None else str(x)).strip()
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
    return float(m.group(0)) if m else math.nan


def _to_int(x) -> Optional[int]:
    s = ("" if x is None else str(x)).strip()
    m = re.search(r"[-+]?\d+", s)
    return int(m.group(0)) if m else None


def _read_samsung_csv_rows(path: str) -> List[Dict[str, str]]:
    """Read Samsung Health CSV using stdlib csv, skipping first metadata line.

    Returns list of dict rows.
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    # Skip first line (metadata) deterministically
    lines = text.splitlines()
    content = "\n".join(lines[1:]) if len(lines) > 1 else ""
    reader = csv.DictReader(io.StringIO(content))
    return [row for row in reader]


def load_weight_df(weight_csv_path: str) -> List[Dict]:
    """Load and normalize weight/composition entries as list of dicts.

    Keys: date (datetime), weight, body_fat, skeletal_muscle_mass, fat_free_mass
    """
    rows = _read_samsung_csv_rows(weight_csv_path)
    keep = ["start_time", "weight", "body_fat", "skeletal_muscle_mass", "fat_free_mass"]
    out: List[Dict] = []
    for r in rows:
        rec: Dict = {}
        for k in keep:
            if k in r:
                rec[k] = r.get(k, "")
        if rec:
            # Normalize
            dt = _parse_datetime_str(rec.get("start_time"))
            if dt is None:
                continue
            rec2 = {
                "date": dt,
                "weight": _to_float(rec.get("weight")),
                "body_fat": _to_float(rec.get("body_fat")),
                "skeletal_muscle_mass": _to_float(rec.get("skeletal_muscle_mass")),
                "fat_free_mass": _to_float(rec.get("fat_free_mass")),
            }
            out.append(rec2)
    out.sort(key=lambda x: x["date"])  # chronological
    return out


def load_food_intake_df(food_csv_path: str) -> List[Dict]:
    """Load food intake entries as list of dicts.

    Keys: date (datetime), meal_type (int|None), name, amount (float), unit, calorie (float)
    """
    rows = _read_samsung_csv_rows(food_csv_path)
    keep = ["start_time", "meal_type", "name", "amount", "unit", "calorie"]
    out: List[Dict] = []
    for r in rows:
        rec: Dict = {}
        for k in keep:
            if k in r:
                rec[k] = r.get(k, "")
        if rec:
            dt = _parse_datetime_str(rec.get("start_time"))
            if dt is None:
                continue
            rec2 = {
                "date": dt,
                "meal_type": _to_int(rec.get("meal_type")),
                "name": rec.get("name", ""),
                "amount": _to_float(rec.get("amount")),
                "unit": rec.get("unit", ""),
                "calorie": _to_float(rec.get("calorie")),
            }
            out.append(rec2)
    out.sort(key=lambda x: x["date"])  # chronological
    return out


def compute_daily_calories(food_entries: List[Dict]) -> List[Dict]:
    """Aggregate daily calories from raw food intake entries (list of dicts)."""
    totals: Dict[str, float] = {}
    for rec in food_entries:
        dt = rec.get("date")
        if not isinstance(dt, datetime):
            continue
        key = dt.date().isoformat()
        val = float(rec.get("calorie", 0.0))
        totals[key] = totals.get(key, 0.0) + val
    records = [
        {"date": datetime.fromisoformat(k), "calories": v} for k, v in totals.items()
    ]
    records.sort(key=lambda x: x["date"])
    return records


def load_all(data_dir: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
    """Convenience: load weight entries and daily calories (lists of dicts)."""
    paths = find_data_files(data_dir)
    weight = load_weight_df(paths.weight_csv) if paths.weight_csv else []  # type: ignore
    food = load_food_intake_df(paths.food_csv) if paths.food_csv else []  # type: ignore
    daily_cal = compute_daily_calories(food)
    return weight, daily_cal
