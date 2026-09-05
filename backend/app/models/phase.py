"""Phases de suivi et leurs objectifs."""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import CheckConstraint, Date, Double, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PhaseKind(enum.StrEnum):
    FREE = "free"
    BULK = "bulk"
    CUT = "cut"
    MAINTAIN = "maintain"


class Phase(Base, TimestampMixin):
    """Une période de suivi.

    ends_on est inclusif. Aucune contrainte d'exclusion de chevauchement :
    les données réelles contiennent un chevauchement d'un jour entre une
    sèche et le maintien qui la suit.
    """

    __tablename__ = "phase"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="ck_phase_dates_ordered"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[PhaseKind] = mapped_column(
        Enum(PhaseKind, name="phase_kind", native_enum=True), nullable=False
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    weight_target_kg: Mapped[float | None] = mapped_column(Double)
    body_fat_target_pct: Mapped[float | None] = mapped_column(Double)
    skeletal_muscle_target_kg: Mapped[float | None] = mapped_column(Double)
    daily_calories_target: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
