"""Mesures de composition corporelle."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BodyMeasurement(Base, TimestampMixin):
    __tablename__ = "body_measurement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    weight_kg: Mapped[float | None] = mapped_column(Double)
    body_fat_pct: Mapped[float | None] = mapped_column(Double)
    body_fat_mass_kg: Mapped[float | None] = mapped_column(Double)
    skeletal_muscle_mass_kg: Mapped[float | None] = mapped_column(Double)
    skeletal_muscle_pct: Mapped[float | None] = mapped_column(Double)
    fat_free_mass_kg: Mapped[float | None] = mapped_column(Double)
    fat_free_pct: Mapped[float | None] = mapped_column(Double)
    total_body_water_kg: Mapped[float | None] = mapped_column(Double)
    basal_metabolic_rate_kcal: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Double)
