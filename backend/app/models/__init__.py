"""Import de tous les modèles pour peupler Base.metadata."""

from app.models.base import Base
from app.models.body import BodyMeasurement
from app.models.ingestion import IngestionRun, IngestionStatus
from app.models.nutrition import NutritionEntry
from app.models.phase import Phase, PhaseKind
from app.models.photo import Photo
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
    "IngestionRun",
    "IngestionStatus",
    "NutritionEntry",
    "Phase",
    "PhaseKind",
    "Photo",
    "StrengthSet",
    "SwimLength",
    "Workout",
    "WorkoutExtra",
    "WorkoutLocation",
    "WorkoutSample",
]
