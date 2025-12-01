from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

DATA_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PHASES_JSON_DEFAULT = os.path.join(DATA_DIR_DEFAULT, "phases.json")


@dataclass
class Phase:
    name: str
    type: str  # one of: free, bulk, cut, maintain
    start: pd.Timestamp
    end: pd.Timestamp

    @property
    def label(self) -> str:
        return f"{self.name} ({self.type})"


PHASE_TYPES = {"free", "bulk", "cut", "maintain"}


def _parse_date(s: str) -> pd.Timestamp:
    return pd.to_datetime(s, errors="coerce")


def load_phases(
    json_path: Optional[str] = None,
    fallback_range: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None,
) -> List[Phase]:
    path = json_path or PHASES_JSON_DEFAULT
    phases: List[Phase] = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw:
            name = item.get("name", "")
            typ = item.get("type", "free").lower()
            if typ not in PHASE_TYPES:
                typ = "free"
            start = _parse_date(item.get("start"))
            end = _parse_date(item.get("end"))
            if pd.isna(start) or pd.isna(end):
                continue
            phases.append(Phase(name=name, type=typ, start=start, end=end))
    elif fallback_range:
        phases.append(
            Phase(
                name="Default",
                type="free",
                start=fallback_range[0],
                end=fallback_range[1],
            )
        )
    return sorted(phases, key=lambda p: p.start)


def summarize_phase(weight_data: list, daily_cal_data: list, phase: Phase) -> dict:
    """Compute summary metrics for a given phase."""
    # Filter by phase range
    w_filtered = [r for r in weight_data if phase.start <= r["date"] <= phase.end]
    c_filtered = [r for r in daily_cal_data if phase.start <= r["date"] <= phase.end]

    # Convert to DataFrame for easy column access
    w = pd.DataFrame(w_filtered)
    c = pd.DataFrame(c_filtered)

    def delta_with_values(series: pd.Series) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Calcule le delta et retourne (delta, start_value, end_value)."""
        if len(series) == 0:
            return None, None, None
        # Enlever les NaN
        valid = series.dropna()
        if len(valid) == 0:
            return None, None, None
        if len(valid) == 1:
            return 0.0, float(valid.iloc[0]), float(valid.iloc[0])
        return float(valid.iloc[-1] - valid.iloc[0]), float(valid.iloc[0]), float(valid.iloc[-1])
    
    def calculate_monthly_rate(series: pd.Series, days: int) -> Optional[float]:
        """Calcule la vitesse moyenne par mois."""
        if days == 0:
            return None
        delta, _, _ = delta_with_values(series)
        if delta is None:
            return None
        months = days / 30.0
        if months == 0:
            return None
        return delta / months
    
    def calculate_percentage_change(start: Optional[float], end: Optional[float]) -> Optional[float]:
        """Calcule le changement en pourcentage."""
        if start is None or end is None or start == 0:
            return None
        return ((end - start) / start) * 100

    days = int((phase.end - phase.start).days) + 1
    
    weight_delta, weight_start, weight_end = delta_with_values(w["weight"]) if "weight" in w.columns else (None, None, None)
    bf_delta, bf_start, bf_end = delta_with_values(w["body_fat"]) if "body_fat" in w.columns else (None, None, None)
    muscle_delta, muscle_start, muscle_end = delta_with_values(w["skeletal_muscle_mass"]) if "skeletal_muscle_mass" in w.columns else (None, None, None)

    # Calculs de vitesse mensuelle
    weight_monthly = calculate_monthly_rate(w["weight"], days) if "weight" in w.columns else None
    bf_monthly = calculate_monthly_rate(w["body_fat"], days) if "body_fat" in w.columns else None
    muscle_monthly = calculate_monthly_rate(w["skeletal_muscle_mass"], days) if "skeletal_muscle_mass" in w.columns else None
    
    # Calculs de changement en pourcentage
    weight_pct = calculate_percentage_change(weight_start, weight_end)
    bf_pct = calculate_percentage_change(bf_start, bf_end)
    muscle_pct = calculate_percentage_change(muscle_start, muscle_end)

    return {
        "label": phase.label,
        "start": phase.start,
        "end": phase.end,
        "days": days,
        # Poids
        "weight_delta": weight_delta,
        "weight_start": weight_start,
        "weight_end": weight_end,
        "weight_monthly": weight_monthly,
        "weight_pct": weight_pct,
        # Masse grasse
        "body_fat_delta": bf_delta,
        "body_fat_start": bf_start,
        "body_fat_end": bf_end,
        "body_fat_monthly": bf_monthly,
        "body_fat_pct": bf_pct,
        # Masse musculaire
        "skeletal_muscle_delta": muscle_delta,
        "skeletal_muscle_start": muscle_start,
        "skeletal_muscle_end": muscle_end,
        "skeletal_muscle_monthly": muscle_monthly,
        "skeletal_muscle_pct": muscle_pct,
        # Calories
        "avg_daily_calories": (
            float(c["calories"].mean())
            if len(c) > 0 and "calories" in c.columns
            else None
        ),
    }


def phase_boundaries(
    phases: List[Phase], data_range: Optional[tuple] = None
) -> pd.DataFrame:
    """Return a DataFrame of boundaries to plot as vertical lines.

    If data_range is provided (min_date, max_date), only include phase boundaries
    that fall within the data range.
    """
    if not phases:
        return pd.DataFrame(columns=["date", "phase", "type"])
    rows = []
    for p in phases:
        # Only include the phase start if it's within the data range
        if data_range is None or (data_range[0] <= p.start <= data_range[1]):
            rows.append({"date": p.start, "phase": p.name, "type": p.type})
    return (
        pd.DataFrame(rows).sort_values("date")
        if rows
        else pd.DataFrame(columns=["date", "phase", "type"])
    )
