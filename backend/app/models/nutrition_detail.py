"""Macronutriments et micronutriments par repas.

Source distincte de food_intake : aucune clé commune fiable ne relie les
deux (vérifié sur les en-têtes réelles), elles restent deux tables.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NutritionDetail(Base, TimestampMixin):
    __tablename__ = "nutrition_detail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    # Codes Samsung à 6 chiffres (ex. 100002) : un SmallInteger (max 32 767)
    # déborde sur les vraies valeurs, cf. app/models/nutrition.py.
    meal_type: Mapped[int | None] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")

    calories: Mapped[float | None] = mapped_column(Double)
    protein: Mapped[float | None] = mapped_column(Double)
    total_fat: Mapped[float | None] = mapped_column(Double)
    saturated_fat: Mapped[float | None] = mapped_column(Double)
    trans_fat: Mapped[float | None] = mapped_column(Double)
    monosaturated_fat: Mapped[float | None] = mapped_column(Double)
    polysaturated_fat: Mapped[float | None] = mapped_column(Double)
    carbohydrate: Mapped[float | None] = mapped_column(Double)
    dietary_fiber: Mapped[float | None] = mapped_column(Double)
    sugar: Mapped[float | None] = mapped_column(Double)
    added_sugar: Mapped[float | None] = mapped_column(Double)
    cholesterol: Mapped[float | None] = mapped_column(Double)
    sodium: Mapped[float | None] = mapped_column(Double)
    potassium: Mapped[float | None] = mapped_column(Double)
    calcium: Mapped[float | None] = mapped_column(Double)
    iron: Mapped[float | None] = mapped_column(Double)
    vitamin_a: Mapped[float | None] = mapped_column(Double)
    vitamin_c: Mapped[float | None] = mapped_column(Double)
    vitamin_d: Mapped[float | None] = mapped_column(Double)
