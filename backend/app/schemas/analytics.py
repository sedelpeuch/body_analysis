"""Schémas Pydantic exposés par les analyses transverses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class CompositionPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    body_fat_mass_kg: float | None
    fat_free_mass_kg: float | None
    skeletal_muscle_mass_kg: float | None
    total_body_water_kg: float | None
    basal_metabolic_rate_kcal: float | None


class TdeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tdee_kcal: float | None
    mean_intake_kcal: float | None
    weight_slope_kg_per_day: float | None
    is_valid: bool
    reason: str | None
    uncertainty_note: str


class EnergyBalanceDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    intake_kcal: float | None
    expenditure_kcal: float | None
    balance_kcal: float | None


class RestingHrPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    resting_hr: int | None


class LoadBalanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    acute_load: float | None
    chronic_load: float | None
    ratio: float | None
