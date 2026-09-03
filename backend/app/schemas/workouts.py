"""Schémas Pydantic exposés par l'API entraînement."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sport: str
    workout_count: int


class WorkoutSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sport: str
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    distance_m: float | None
    calories_kcal: float | None
    mean_heart_rate: float | None


class WorkoutDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sport: str
    sport_type: int | None
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    distance_m: float | None
    calories_kcal: float | None
    mean_heart_rate: float | None
    max_heart_rate: float | None
    min_heart_rate: float | None
    mean_speed_mps: float | None
    max_speed_mps: float | None
    mean_cadence: float | None
    max_cadence: float | None
    min_altitude_m: float | None
    max_altitude_m: float | None
    altitude_gain_m: float | None
    altitude_loss_m: float | None
    pool_length_m: float | None
    resting_hr: int | None
    has_samples: bool
    has_locations: bool
    has_swim_lengths: bool
    has_strength_sets: bool


class SamplePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: datetime
    heart_rate: float | None
    speed_mps: float | None
    distance_m: float | None
    cadence: float | None
    altitude_m: float | None


class TrackOut(BaseModel):
    """GeoJSON LineString — pas de bandeau from_attributes, construit à la main."""

    type: str = "LineString"
    coordinates: list[tuple[float, float]]


class SplitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    distance_m: float
    duration_s: float
    pace_s_per_km: float | None
    mean_heart_rate: float | None


class HrZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone: int
    label: str
    seconds: float


class CardiacDriftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_half_mean_hr: float | None
    second_half_mean_hr: float | None
    drift_pct: float | None


class SwolfByStrokeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stroke_type: str
    length_count: int
    mean_swolf: float | None
    mean_duration_s: float | None


class StrengthSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    idx: int
    reps: int | None
    weight_kg: float | None
    duration_s: float | None


class StrengthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sets: list[StrengthSetOut]
    set_count: int
    total_volume_kg: float | None
    total_reps: int | None


class WorkoutStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_count: int
    total_duration_ms: int
    total_distance_m: float
    total_calories_kcal: float


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    workout_id: int
    value: float
    at: datetime


class WorkoutCalendarCellOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    value: float | None
