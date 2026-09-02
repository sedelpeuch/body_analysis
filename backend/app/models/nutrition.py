"""Entrées du journal alimentaire."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NutritionEntry(Base, TimestampMixin):
    __tablename__ = "nutrition_entry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    meal_type: Mapped[int | None] = mapped_column(SmallInteger, index=True)
    food_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    amount: Mapped[float | None] = mapped_column(Double)
    unit_code: Mapped[int | None] = mapped_column(SmallInteger)
    calories: Mapped[float | None] = mapped_column(Double)
