from __future__ import annotations

import calendar
import csv
import glob
import io
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime

ENV = os.environ.get("ENV", "dev")
if ENV == "production":
    DATA_DIR_DEFAULT = "/app/data"
else:
    DATA_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@dataclass
class DataPaths:
    weight_csv: str | None
    food_csv: str | None
    exercise_csv: str | None


def find_data_files(data_dir: str | None = None) -> DataPaths:
    """Locate Samsung Health export CSVs in the given data directory.

    If multiple files match, returns the most recent one based on the date
    in the filename (format: com.samsung.health.*.YYYYMMDD.csv).
    """
    data_dir = data_dir or DATA_DIR_DEFAULT
    weight_matches = glob.glob(
        os.path.join(data_dir, "com.samsung.health.weight.*.csv"),
    )
    food_matches = glob.glob(
        os.path.join(data_dir, "com.samsung.health.food_intake.*.csv"),
    )

    # Pour l'exercice, filtrer pour le format exact: com.samsung.shealth.exercise.YYYYMMDDHHMMSS.csv
    exercise_all = glob.glob(
        os.path.join(data_dir, "com.samsung.shealth.exercise.*.csv"),
    )
    exercise_matches = [
        f
        for f in exercise_all
        if re.match(r".*com\.samsung\.shealth\.exercise\.\d{14}\.csv$", f)
    ]

    def get_latest_file(matches: list) -> str | None:
        """Return the most recent file based on date in filename."""
        if not matches:
            return None
        # Sort by filename (dates in YYYYMMDD format sort correctly alphabetically)
        return sorted(matches)[-1]

    return DataPaths(
        weight_csv=get_latest_file(weight_matches),
        food_csv=get_latest_file(food_matches),
        exercise_csv=get_latest_file(exercise_matches),
    )


def _parse_datetime_str(s: str | None) -> datetime | None:
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


def _to_int(x) -> int | None:
    s = ("" if x is None else str(x)).strip()
    m = re.search(r"[-+]?\d+", s)
    return int(m.group(0)) if m else None


def _read_samsung_csv_rows(path: str) -> list[dict[str, str]]:
    """Read Samsung Health CSV using stdlib csv, skipping first metadata line.

    Returns list of dict rows.
    """
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    # Skip first line (metadata) deterministically
    lines = text.splitlines()
    content = "\n".join(lines[1:]) if len(lines) > 1 else ""
    reader = csv.DictReader(io.StringIO(content))
    return [row for row in reader]


def load_weight_df(weight_csv_path: str) -> list[dict]:
    """Load and normalize weight/composition entries as list of dicts.

    Keys: date (datetime), weight, body_fat, skeletal_muscle_mass, fat_free_mass
    """
    rows = _read_samsung_csv_rows(weight_csv_path)
    keep = ["start_time", "weight", "body_fat", "skeletal_muscle_mass", "fat_free_mass"]
    out: list[dict] = []
    for r in rows:
        rec: dict = {}
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


def load_food_intake_df(food_csv_path: str) -> list[dict]:
    """Load food intake entries as list of dicts.

    Keys: date (datetime), meal_type (int|None), name, amount (float), unit, calorie (float)
    """
    rows = _read_samsung_csv_rows(food_csv_path)
    keep = ["start_time", "meal_type", "name", "amount", "unit", "calorie"]
    out: list[dict] = []
    for r in rows:
        rec: dict = {}
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


def load_exercise_df(exercise_csv_path: str) -> list[dict]:
    """Load exercise entries as list of dicts.

    Keys: date (datetime), exercise_type (int|None), name, duration (float), calorie (float)
    """
    rows = _read_samsung_csv_rows(exercise_csv_path)
    keep = [
        "mission_value",
        "race_target",
        "subset_data",
        "start_longitude",
        "routine_datauuid",
        "total_calorie",
        "completion_status",
        "activity_type",
        "sensing_status",
        "source_type",
        "mission_type",
        "tracking_status",
        "reward_status",
        "heart_rate_sample_count",
        "start_latitude",
        "mission_extra_value",
        "heart_rate_deviceuuid",
        "location_data_internal",
        "custom_id",
        "additional_internal",
        "com.samsung.health.exercise.duration",
        "com.samsung.health.exercise.additional",
        "com.samsung.health.exercise.create_sh_ver",
        "com.samsung.health.exercise.location_data",
        "com.samsung.health.exercise.start_time",
        "com.samsung.health.exercise.exercise_type",
        "com.samsung.health.exercise.max_altitude",
        "com.samsung.health.exercise.incline_distance",
        "com.samsung.health.exercise.mean_heart_rate",
        "com.samsung.health.exercise.count_type",
        "com.samsung.health.exercise.min_altitude",
        "com.samsung.health.exercise.modify_sh_ver",
        "com.samsung.health.exercise.max_heart_rate",
        "com.samsung.health.exercise.update_time",
        "com.samsung.health.exercise.create_time",
        "com.samsung.health.exercise.max_speed",
        "com.samsung.health.exercise.mean_cadence",
        "com.samsung.health.exercise.min_heart_rate",
        "com.samsung.health.exercise.count",
        "com.samsung.health.exercise.distance",
        "com.samsung.health.exercise.calorie",
        "com.samsung.health.exercise.max_cadence",
        "com.samsung.health.exercise.decline_distance",
        "com.samsung.health.exercise.vo2_max",
        "com.samsung.health.exercise.time_offset",
        "com.samsung.health.exercise.deviceuuid",
        "com.samsung.health.exercise.comment",
        "com.samsung.health.exercise.live_data",
        "com.samsung.health.exercise.mean_speed",
        "com.samsung.health.exercise.pkg_name",
        "com.samsung.health.exercise.altitude_gain",
        "com.samsung.health.exercise.altitude_loss",
        "com.samsung.health.exercise.end_time",
        "com.samsung.health.exercise.datauuid",
        "com.samsung.health.exercise.sweat_loss",
    ]
    out: list[dict] = []
    for r in rows:
        rec: dict = {}
        for k in keep:
            if k in r:
                dt = _parse_datetime_str(
                    r.get("com.samsung.health.exercise.start_time"),
                )
                if dt is not None:
                    if dt.date() >= datetime(2024, 8, 12).date():
                        rec["date"] = dt
                        rec["distance"] = _to_float(
                            r.get("com.samsung.health.exercise.distance"),
                        )
                        rec["duration"] = _to_float(
                            r.get("com.samsung.health.exercise.duration"),
                        )
                        rec["calorie"] = _to_float(
                            r.get("com.samsung.health.exercise.calorie"),
                        )
                        rec["exercise_type"] = _to_int(
                            r.get("com.samsung.health.exercise.exercise_type"),
                        )
                        rec["subset_data"] = r.get("subset_data", "")
                        rec["heart_rate"] = _to_float(
                            r.get("com.samsung.health.exercise.mean_heart_rate"),
                        )
                        rec["heart_rate_max"] = _to_float(
                            r.get("com.samsung.health.exercise.max_heart_rate"),
                        )
                        rec["heart_rate_min"] = _to_float(
                            r.get("com.samsung.health.exercise.min_heart_rate"),
                        )
                        rec["longitude"] = _to_float(r.get("start_longitude"))
                        rec["latitude"] = _to_float(r.get("start_latitude"))
                        rec["min_altitude"] = _to_float(
                            r.get("com.samsung.health.exercise.min_altitude"),
                        )
                        rec["max_altitude"] = _to_float(
                            r.get("com.samsung.health.exercise.max_altitude"),
                        )
                        rec["altitude_gain"] = _to_float(
                            r.get("com.samsung.health.exercise.altitude_gain"),
                        )
                        rec["altitude_loss"] = _to_float(
                            r.get("com.samsung.health.exercise.altitude_loss"),
                        )
                        rec["additionnal"] = r.get(
                            "com.samsung.health.exercise.additional",
                            "",
                        )
                        rec["location"] = r.get(
                            "com.samsung.health.exercise.location_data",
                            "",
                        )

        if rec:
            out.append(rec)
    out.sort(key=lambda x: x["date"])
    return out


def compute_daily_calories(food_entries: list[dict]) -> list[dict]:
    """Aggregate daily calories from raw food intake entries (list of dicts)."""
    totals: dict[str, float] = {}
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


def load_all(data_dir: str | None = None) -> tuple[list[dict], list[dict]]:
    """Convenience: load weight entries and daily calories (lists of dicts)."""
    paths = find_data_files(data_dir)
    weight = load_weight_df(paths.weight_csv) if paths.weight_csv else []  # type: ignore
    food = load_food_intake_df(paths.food_csv) if paths.food_csv else []  # type: ignore
    daily_cal = compute_daily_calories(food)
    return weight, daily_cal
