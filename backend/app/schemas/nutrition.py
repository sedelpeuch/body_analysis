"""Schémas Pydantic exposés par l'API nutrition."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DailyNutritionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    calories: float | None
    entry_count: int


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: datetime
    food_name: str
    meal_type_label: str
    amount: float | None
    unit_label: str
    calories: float | None


class MealTypeShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_type_label: str
    calories: float | None
    entry_count: int


class TopFoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    food_name: str
    entry_count: int
    total_calories: float | None


class NutritionBreakdownOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    by_meal_type: list[MealTypeShareOut]
    top_foods: list[TopFoodOut]
