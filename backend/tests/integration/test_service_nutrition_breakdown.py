"""Tests d'intégration de la répartition nutrition par repas."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.models import NutritionEntry
from app.services.nutrition import get_breakdown

pytestmark = pytest.mark.asyncio


async def test_get_breakdown_groups_by_meal_type_and_ranks_foods(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            NutritionEntry(
                source_uuid="brk-1",
                consumed_at=datetime(2026, 4, 1, 8, tzinfo=UTC),
                food_name="Avoine",
                meal_type=100001,
                unit_code=120001,
                calories=350.0,
            ),
            NutritionEntry(
                source_uuid="brk-2",
                consumed_at=datetime(2026, 4, 1, 12, tzinfo=UTC),
                food_name="Poulet",
                meal_type=100002,
                unit_code=120001,
                calories=500.0,
            ),
            NutritionEntry(
                source_uuid="brk-3",
                consumed_at=datetime(2026, 4, 2, 12, tzinfo=UTC),
                food_name="Poulet",
                meal_type=100002,
                unit_code=120001,
                calories=520.0,
            ),
        ],
    )
    await session.commit()

    breakdown = await get_breakdown(
        session,
        DateRange(start=date(2026, 4, 1), end=date(2026, 4, 30)),
    )

    shares = {s.meal_type_label: s for s in breakdown.by_meal_type}
    assert shares["Petit-déjeuner"].calories == pytest.approx(350.0)
    assert shares["Déjeuner"].calories == pytest.approx(1020.0)
    assert breakdown.top_foods[0].food_name == "Poulet"
    assert breakdown.top_foods[0].entry_count == 2
