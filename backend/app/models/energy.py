"""Décomposition quotidienne de la dépense énergétique.

day est une date calendaire, pas un instant : com.samsung.shealth.calories_
burned.details ne porte aucune colonne time_offset, seule sa partie date est
fiable.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Double, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class EnergyExpenditure(Base, TimestampMixin):
    __tablename__ = "energy_expenditure"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    rest_calorie: Mapped[float | None] = mapped_column(Double)
    active_calorie: Mapped[float | None] = mapped_column(Double)
    tef_calorie: Mapped[float | None] = mapped_column(Double)
    active_time_ms: Mapped[int | None] = mapped_column(Integer)
    total_exercise_calories: Mapped[float | None] = mapped_column(Double)
