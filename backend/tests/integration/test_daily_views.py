"""Tests des vues matérialisées quotidiennes."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.refresh import refresh_materialized_views
from app.ingestion.samsung.loader import (
    upsert_body_measurements,
    upsert_nutrition_entries,
)
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
)
from app.models import BodyMeasurement, NutritionEntry


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (BodyMeasurement, NutritionEntry):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_daily_body_keeps_last_measurement_of_the_day(
    session: AsyncSession,
) -> None:
    await upsert_body_measurements(
        session,
        [
            BodyMeasurementRecord(
                source_uuid="morning",
                measured_at=datetime(2026, 8, 31, 6, 0, tzinfo=UTC),
                weight_kg=66.0,
            ),
            BodyMeasurementRecord(
                source_uuid="evening",
                measured_at=datetime(2026, 8, 31, 20, 0, tzinfo=UTC),
                weight_kg=65.4,
            ),
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    rows = (
        await session.execute(text("SELECT day, weight_kg FROM mv_daily_body"))
    ).all()
    assert len(rows) == 1
    assert rows[0].weight_kg == 65.4


async def test_daily_nutrition_sums_calories(session: AsyncSession) -> None:
    await upsert_nutrition_entries(
        session,
        [
            NutritionEntryRecord(
                source_uuid=f"entry-{index}",
                consumed_at=datetime(2026, 8, 31, 12, index, tzinfo=UTC),
                calories=100.0,
            )
            for index in range(3)
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    row = (
        await session.execute(
            text("SELECT calories, entry_count FROM mv_daily_nutrition")
        )
    ).one()
    assert row.calories == 300.0
    assert row.entry_count == 3


async def test_day_boundary_uses_paris_time(session: AsyncSession) -> None:
    """Le 31 août à 23 h 30 UTC est déjà le 1er septembre à Paris."""
    await upsert_nutrition_entries(
        session,
        [
            NutritionEntryRecord(
                source_uuid="late",
                consumed_at=datetime(2026, 8, 31, 23, 30, tzinfo=UTC),
                calories=50.0,
            )
        ],
    )

    await refresh_materialized_views(session, concurrently=False)

    row = (await session.execute(text("SELECT day FROM mv_daily_nutrition"))).one()
    assert str(row.day) == "2026-09-01"


async def test_concurrent_refresh_works(session: AsyncSession) -> None:
    """Vérifie que les index uniques requis par CONCURRENTLY existent."""
    await refresh_materialized_views(session, concurrently=False)

    await refresh_materialized_views(session, concurrently=True)
