"""Service nutrition : entrées quotidiennes et listes paginées."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.labels import meal_type_label, unit_label
from app.api.deps import DateRange
from app.models import NutritionEntry

NUTRITION_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class DailyNutritionRow:
    day: date
    calories: float | None
    entry_count: int


async def get_daily(session: AsyncSession, date_range: DateRange) -> list[DailyNutritionRow]:
    where_parts: list[str] = []
    params: dict[str, date] = {}
    if date_range.start is not None:
        where_parts.append("day >= :start")
        params["start"] = date_range.start
    if date_range.end is not None:
        where_parts.append("day <= :end")
        params["end"] = date_range.end

    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = text(f"SELECT day, calories, entry_count FROM mv_daily_nutrition{where_clause} ORDER BY day")
    rows = (await session.execute(sql, params)).all()
    return [
        DailyNutritionRow(day=row.day, calories=row.calories, entry_count=row.entry_count)
        for row in rows
    ]


@dataclass(frozen=True, slots=True)
class EntryRow:
    at: datetime
    food_name: str
    meal_type_label: str
    amount: float | None
    unit_label: str
    calories: float | None


def _entries_query(date_range: DateRange):
    query = select(NutritionEntry).order_by(NutritionEntry.consumed_at)
    if date_range.start is not None:
        query = query.where(NutritionEntry.consumed_at >= date_range.start)
    if date_range.end is not None:
        query = query.where(NutritionEntry.consumed_at <= date_range.end)
    return query


async def list_entries(
    session: AsyncSession, date_range: DateRange, page: int
) -> tuple[list[EntryRow], int]:
    base_query = _entries_query(date_range)
    total = (
        await session.execute(select(func.count()).select_from(base_query.subquery()))
    ).scalar_one()

    offset = (page - 1) * NUTRITION_PAGE_SIZE
    rows = (
        await session.execute(base_query.limit(NUTRITION_PAGE_SIZE).offset(offset))
    ).scalars().all()

    entries = [
        EntryRow(
            at=row.consumed_at,
            food_name=row.food_name,
            meal_type_label=meal_type_label(row.meal_type),
            amount=row.amount,
            unit_label=unit_label(row.unit_code),
            calories=row.calories,
        )
        for row in rows
    ]
    return entries, total
