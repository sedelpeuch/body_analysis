"""Import de tous les modèles pour peupler Base.metadata."""

from app.models.activity import DailyActivity, StepDailyTrend
from app.models.base import Base
from app.models.body import BodyMeasurement
from app.models.energy import EnergyExpenditure
from app.models.ingestion import IngestionRun, IngestionStatus
from app.models.nutrition import NutritionEntry
from app.models.nutrition_detail import NutritionDetail
from app.models.phase import Phase, PhaseKind
from app.models.photo import Photo
from app.models.sleep import SleepSession, SleepStage
from app.models.vitals import (
    HeartRateReading,
    HrvReading,
    OxygenSaturationReading,
    RespiratoryRateReading,
    SkinTemperatureReading,
    StressReading,
)
from app.models.workout import (
    StrengthSet,
    SwimLength,
    Workout,
    WorkoutExtra,
    WorkoutLocation,
    WorkoutSample,
)

__all__ = [
    "Base",
    "BodyMeasurement",
    "DailyActivity",
    "EnergyExpenditure",
    "HeartRateReading",
    "HrvReading",
    "IngestionRun",
    "IngestionStatus",
    "NutritionDetail",
    "NutritionEntry",
    "OxygenSaturationReading",
    "Phase",
    "PhaseKind",
    "Photo",
    "RespiratoryRateReading",
    "SkinTemperatureReading",
    "SleepSession",
    "SleepStage",
    "StepDailyTrend",
    "StrengthSet",
    "StressReading",
    "SwimLength",
    "Workout",
    "WorkoutExtra",
    "WorkoutLocation",
    "WorkoutSample",
]
