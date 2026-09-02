"""Schémas Pydantic exposés par l'API phases."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import PhaseKind


class PhaseCreate(BaseModel):
    name: str
    kind: PhaseKind
    starts_on: date
    ends_on: date
    weight_target_kg: float | None = None
    body_fat_target_pct: float | None = None
    skeletal_muscle_target_kg: float | None = None
    daily_calories_target: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _ends_not_before_starts(self) -> PhaseCreate:
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on doit être postérieure ou égale à starts_on")
        return self


class PhaseUpdate(BaseModel):
    name: str | None = None
    kind: PhaseKind | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    weight_target_kg: float | None = None
    body_fat_target_pct: float | None = None
    skeletal_muscle_target_kg: float | None = None
    daily_calories_target: int | None = None
    notes: str | None = None


class PhaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: PhaseKind
    starts_on: date
    ends_on: date
    weight_target_kg: float | None
    body_fat_target_pct: float | None
    skeletal_muscle_target_kg: float | None
    daily_calories_target: int | None
    notes: str | None
