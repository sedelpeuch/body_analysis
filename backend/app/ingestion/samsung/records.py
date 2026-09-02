"""Dataclasses du domaine d'ingestion.

Ces types sont la frontière entre le mapper, qui connaît le format Samsung,
et le loader, qui connaît la base. Aucun des deux n'a besoin de l'autre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BodyMeasurementRecord:
    source_uuid: str
    measured_at: datetime
    weight_kg: float | None = None
    body_fat_pct: float | None = None
    body_fat_mass_kg: float | None = None
    skeletal_muscle_mass_kg: float | None = None
    skeletal_muscle_pct: float | None = None
    fat_free_mass_kg: float | None = None
    fat_free_pct: float | None = None
    total_body_water_kg: float | None = None
    basal_metabolic_rate_kcal: int | None = None
    height_cm: float | None = None


@dataclass(frozen=True, slots=True)
class NutritionEntryRecord:
    source_uuid: str
    consumed_at: datetime
    food_name: str = ""
    meal_type: int | None = None
    amount: float | None = None
    unit_code: int | None = None
    calories: float | None = None


@dataclass(frozen=True, slots=True)
class NutritionDetailRecord:
    source_uuid: str
    consumed_at: datetime
    meal_type: int | None = None
    title: str = ""
    calories: float | None = None
    protein: float | None = None
    total_fat: float | None = None
    saturated_fat: float | None = None
    trans_fat: float | None = None
    monosaturated_fat: float | None = None
    polysaturated_fat: float | None = None
    carbohydrate: float | None = None
    dietary_fiber: float | None = None
    sugar: float | None = None
    added_sugar: float | None = None
    cholesterol: float | None = None
    sodium: float | None = None
    potassium: float | None = None
    calcium: float | None = None
    iron: float | None = None
    vitamin_a: float | None = None
    vitamin_c: float | None = None
    vitamin_d: float | None = None


@dataclass(frozen=True, slots=True)
class EnergyExpenditureRecord:
    source_uuid: str
    day: date
    rest_calorie: float | None = None
    active_calorie: float | None = None
    tef_calorie: float | None = None
    active_time_ms: int | None = None
    total_exercise_calories: float | None = None


@dataclass(frozen=True, slots=True)
class SleepSessionRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    original_wake_up_time: datetime | None = None
    efficiency: float | None = None
    efficiency_with_latency: float | None = None
    physical_recovery: int | None = None
    mental_recovery: int | None = None
    deep_score: int | None = None
    rem_score: int | None = None
    wake_score: int | None = None
    nap_score: int | None = None
    latency_score: int | None = None
    sleep_latency: int | None = None
    total_rem_duration: int | None = None
    total_light_duration: int | None = None
    sleep_duration: int | None = None
    sleep_score: int | None = None
    has_sleep_data: int | None = None
    sleep_type: int | None = None


@dataclass(frozen=True, slots=True)
class SleepStageRecord:
    source_uuid: str
    started_at: datetime
    sleep_source_uuid: str | None = None
    ended_at: datetime | None = None
    stage: int | None = None


@dataclass(frozen=True, slots=True)
class HrvReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    avg_sdnn: float | None = None
    avg_rmssd: float | None = None
    sample_count: int = 0


@dataclass(frozen=True, slots=True)
class HeartRateReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    mean_heart_rate: float | None = None
    min_heart_rate: float | None = None
    max_heart_rate: float | None = None
    heart_beat_count: int | None = None
    tag_id: int | None = None


@dataclass(frozen=True, slots=True)
class StressReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    score: float | None = None
    min_score: float | None = None
    max_score: float | None = None
    tag_id: int | None = None


@dataclass(frozen=True, slots=True)
class RespiratoryRateReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    average: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None


@dataclass(frozen=True, slots=True)
class SkinTemperatureReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    temperature: float | None = None
    min_temperature: float | None = None
    max_temperature: float | None = None
    baseline: float | None = None


@dataclass(frozen=True, slots=True)
class OxygenSaturationReadingRecord:
    source_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    spo2: float | None = None
    heart_rate: float | None = None
    tag_id: int | None = None


@dataclass(frozen=True, slots=True)
class DailyActivityRecord:
    source_uuid: str
    day: date
    step_count: int | None = None
    active_time_ms: int | None = None
    calorie: float | None = None
    distance_m: float | None = None
    floor_count: int | None = None
    score: int | None = None
    exercise_time_ms: int | None = None
    run_time_ms: int | None = None
    walk_time_ms: int | None = None
    longest_active_time_ms: int | None = None
    move_hourly_count: int | None = None


@dataclass(frozen=True, slots=True)
class StepDailyTrendRecord:
    source_uuid: str
    day: date
    count: int | None = None
    distance_m: float | None = None
    calorie: float | None = None
    speed: float | None = None
    source_type: int | None = None


@dataclass(frozen=True, slots=True)
class SampleRecord:
    at: datetime
    elapsed_ms: int | None = None
    heart_rate: int | None = None
    speed_mps: float | None = None
    distance_m: float | None = None
    calories_kcal: float | None = None
    cadence: int | None = None
    segment: int | None = None


@dataclass(frozen=True, slots=True)
class LocationRecord:
    at: datetime
    latitude: float
    longitude: float
    altitude_m: float | None = None
    accuracy_m: float | None = None


@dataclass(frozen=True, slots=True)
class SwimLengthRecord:
    idx: int
    duration_ms: int | None = None
    stroke_count: int | None = None
    stroke_type: str | None = None
    resting_time_ms: int | None = None


@dataclass(frozen=True, slots=True)
class StrengthSetRecord:
    idx: int
    duration_s: float | None = None
    reps: int | None = None
    weight_kg: float | None = None
    weight_unit: str | None = None


@dataclass(frozen=True, slots=True)
class ExtraRecord:
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WorkoutRecord:
    source_uuid: str
    started_at: datetime
    sport: str
    sport_type: int | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    distance_m: float | None = None
    calories_kcal: float | None = None
    mean_heart_rate: float | None = None
    max_heart_rate: float | None = None
    min_heart_rate: float | None = None
    mean_speed_mps: float | None = None
    max_speed_mps: float | None = None
    mean_cadence: float | None = None
    max_cadence: float | None = None
    min_altitude_m: float | None = None
    max_altitude_m: float | None = None
    altitude_gain_m: float | None = None
    altitude_loss_m: float | None = None
    start_latitude: float | None = None
    start_longitude: float | None = None
    vo2_max: float | None = None
    sweat_loss_ml: float | None = None
    pool_length_m: float | None = None
    max_hr_custom: int | None = None
    max_hr_auto: int | None = None
    hr_aerobic_threshold: int | None = None
    hr_anaerobic_threshold: int | None = None
    resting_hr: int | None = None


@dataclass(frozen=True, slots=True)
class WorkoutBundle:
    """Une séance et tout ce qui en dépend."""

    workout: WorkoutRecord
    samples: list[SampleRecord] = field(default_factory=list)
    locations: list[LocationRecord] = field(default_factory=list)
    swim_lengths: list[SwimLengthRecord] = field(default_factory=list)
    strength_sets: list[StrengthSetRecord] = field(default_factory=list)
    extras: list[ExtraRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PhaseRecord:
    name: str
    kind: str
    starts_on: date
    ends_on: date
    weight_target_kg: float | None = None
    body_fat_target_pct: float | None = None
    skeletal_muscle_target_kg: float | None = None
    daily_calories_target: int | None = None
