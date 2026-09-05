"""Schémas Pydantic exposés par l'API corps."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: datetime
    weight_kg: float | None
    body_fat_pct: float | None
    body_fat_mass_kg: float | None
    skeletal_muscle_mass_kg: float | None
    fat_free_mass_kg: float | None
    total_body_water_kg: float | None
    basal_metabolic_rate_kcal: float | None


class TimeseriesPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: date
    value: float | None


class CalendarCellOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    value: float | None


class DeltaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    window_days: int
    start_value: float | None
    end_value: float | None
    change: float | None


class BodySummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latest: MeasurementOut | None
    weight_deltas: list[DeltaOut]
    current_phase_id: int | None
