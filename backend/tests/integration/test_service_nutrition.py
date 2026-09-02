"""Tests d'intégration du service nutrition."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.models import NutritionEntry
from app.services.nutrition import NUTRITION_PAGE_SIZE, get_daily, list_entries

pytestmark = pytest.mark.asyncio


async def _entry(session: AsyncSession, *, uid: str, at: datetime, calories: float | None) -> None:
    session.add(
        NutritionEntry(
            source_uuid=uid,
            consumed_at=at,
            food_name="Poulet",
            meal_type=100002,
            unit_code=120001,
            calories=calories,
        )
    )
    await session.commit()


async def test_get_daily_uses_mv_daily_nutrition(session: AsyncSession) -> None:
    await _entry(
        session,
        uid="nut-1-unique-2099",
        at=datetime(2099, 4, 1, 12, tzinfo=timezone.utc),
        calories=500.0,
    )
    await session.execute(text("REFRESH MATERIALIZED VIEW mv_daily_nutrition"))
    await session.commit()

    result = await get_daily(session, DateRange(start=date(2099, 4, 1), end=date(2099, 4, 30)))

    matching = [r for r in result if r.day == date(2099, 4, 1)]
    assert matching[0].calories == pytest.approx(500.0)
    assert matching[0].entry_count == 1


async def test_list_entries_translates_labels(session: AsyncSession) -> None:
    await _entry(
        session,
        uid="nut-2-unique-2099",
        at=datetime(2098, 4, 1, 8, tzinfo=timezone.utc),
        calories=300.0,
    )

    entries, total = await list_entries(
        session,
        DateRange(start=date(2098, 4, 1), end=date(2098, 4, 2)),
        page=1,
    )

    assert total == 1
    assert entries[0].meal_type_label == "Déjeuner"
    assert entries[0].unit_label == "Grammes"


async def test_list_entries_paginates_by_fixed_page_size(session: AsyncSession) -> None:
    for i in range(NUTRITION_PAGE_SIZE + 5):
        await _entry(
            session,
            uid=f"nut-page-{i}-unique-2099",
            at=datetime(2097, 5, 1, 8, tzinfo=timezone.utc),
            calories=100.0,
        )

    page1, total = await list_entries(
        session,
        DateRange(start=date(2097, 5, 1), end=date(2097, 5, 2)),
        page=1,
    )
    page2, _ = await list_entries(
        session,
        DateRange(start=date(2097, 5, 1), end=date(2097, 5, 2)),
        page=2,
    )

    assert total == NUTRITION_PAGE_SIZE + 5
    assert len(page1) == NUTRITION_PAGE_SIZE
    assert len(page2) == 5
