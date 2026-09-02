"""Séances et leurs séries filles.

Les cinq tables filles vivent ici avec Workout : leur schéma est une seule
décision et elles ne changent jamais séparément.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Workout(Base, TimestampMixin):
    __tablename__ = "workout"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)

    sport_type: Mapped[int | None] = mapped_column(Integer, index=True)
    sport: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    distance_m: Mapped[float | None] = mapped_column(Double)
    calories_kcal: Mapped[float | None] = mapped_column(Double)
    mean_heart_rate: Mapped[float | None] = mapped_column(Double)
    max_heart_rate: Mapped[float | None] = mapped_column(Double)
    min_heart_rate: Mapped[float | None] = mapped_column(Double)
    mean_speed_mps: Mapped[float | None] = mapped_column(Double)
    max_speed_mps: Mapped[float | None] = mapped_column(Double)
    mean_cadence: Mapped[float | None] = mapped_column(Double)
    max_cadence: Mapped[float | None] = mapped_column(Double)
    min_altitude_m: Mapped[float | None] = mapped_column(Double)
    max_altitude_m: Mapped[float | None] = mapped_column(Double)
    altitude_gain_m: Mapped[float | None] = mapped_column(Double)
    altitude_loss_m: Mapped[float | None] = mapped_column(Double)
    start_latitude: Mapped[float | None] = mapped_column(Double)
    start_longitude: Mapped[float | None] = mapped_column(Double)

    # Conservés pour fidélité à la source, mais vides dans les données
    # réelles : aucune vue ne doit les exposer (cf. spec 4.4).
    vo2_max: Mapped[float | None] = mapped_column(Double)
    sweat_loss_ml: Mapped[float | None] = mapped_column(Double)

    pool_length_m: Mapped[float | None] = mapped_column(Double)
    max_hr_custom: Mapped[int | None] = mapped_column(SmallInteger)
    max_hr_auto: Mapped[int | None] = mapped_column(SmallInteger)
    hr_aerobic_threshold: Mapped[int | None] = mapped_column(SmallInteger)
    hr_anaerobic_threshold: Mapped[int | None] = mapped_column(SmallInteger)
    resting_hr: Mapped[int | None] = mapped_column(SmallInteger)

    # Évitent une sous-requête à l'affichage des listes de séances.
    has_samples: Mapped[bool] = mapped_column(nullable=False, default=False)
    has_locations: Mapped[bool] = mapped_column(nullable=False, default=False)
    has_swim_lengths: Mapped[bool] = mapped_column(nullable=False, default=False)
    has_strength_sets: Mapped[bool] = mapped_column(nullable=False, default=False)


class WorkoutSample(Base):
    """Échantillon intra-séance. ~2,8 M lignes sur les données réelles."""

    __tablename__ = "workout_sample"
    __table_args__ = (
        Index("ix_workout_sample_at_brin", "at", postgresql_using="brin"),
    )

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    elapsed_ms: Mapped[int | None] = mapped_column(BigInteger)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger)
    speed_mps: Mapped[float | None] = mapped_column(Double)
    distance_m: Mapped[float | None] = mapped_column(Double)
    calories_kcal: Mapped[float | None] = mapped_column(Double)
    cadence: Mapped[int | None] = mapped_column(SmallInteger)
    segment: Mapped[int | None] = mapped_column(SmallInteger)


class WorkoutLocation(Base):
    """Point GPS. ~590 k lignes sur les données réelles."""

    __tablename__ = "workout_location"
    __table_args__ = (
        Index("ix_workout_location_at_brin", "at", postgresql_using="brin"),
    )

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    altitude_m: Mapped[float | None] = mapped_column(Double)
    accuracy_m: Mapped[float | None] = mapped_column(Double)


class SwimLength(Base):
    """Une longueur de bassin. Permet le SWOLF et l'analyse par nage."""

    __tablename__ = "swim_length"

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    idx: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer)
    stroke_count: Mapped[int | None] = mapped_column(SmallInteger)
    stroke_type: Mapped[str | None] = mapped_column(Text, index=True)
    resting_time_ms: Mapped[int | None] = mapped_column(Integer)


class StrengthSet(Base):
    """Une série de musculation, issue de subset_data.

    1 531 séances réelles en portent ; l'application Streamlit s'en servait
    seulement pour deviner le sport puis jetait les valeurs.
    """

    __tablename__ = "strength_set"

    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        primary_key=True,
    )
    idx: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    duration_s: Mapped[float | None] = mapped_column(Double)
    reps: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[float | None] = mapped_column(Double)
    weight_unit: Mapped[str | None] = mapped_column(Text)


class WorkoutExtra(Base):
    """Charges utiles annexes hétérogènes, conservées en JSONB.

    Les modéliser en colonnes serait du travail perdu pour 150 séances aux
    schémas disparates (métriques Myotest, notamment).
    """

    __tablename__ = "workout_extra"
    __table_args__ = (
        UniqueConstraint("workout_id", "kind", name="uq_workout_extra_kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
