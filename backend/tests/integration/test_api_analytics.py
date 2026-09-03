"""Tests d'intégration des endpoints /api/body/composition et /api/analytics/*."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.models import BodyMeasurement, NutritionEntry, Workout, WorkoutSample

pytestmark = pytest.mark.asyncio


async def _clean(session: AsyncSession) -> None:
    for model in (WorkoutSample, Workout, NutritionEntry, BodyMeasurement):
        await session.execute(model.__table__.delete())
    await session.commit()


async def _refresh(session: AsyncSession) -> None:
    for view in ("mv_daily_body", "mv_daily_nutrition", "mv_daily_training"):
        await session.execute(text(f"REFRESH MATERIALIZED VIEW {view}"))
    await session.commit()


@pytest.fixture
async def client(session: AsyncSession):
    await _clean(session)
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as opened:
            yield opened
    finally:
        app.dependency_overrides.clear()


async def test_get_composition_returns_kg_series(
    session: AsyncSession, client: AsyncClient
):
    session.add(
        BodyMeasurement(
            source_uuid="comp-1",
            measured_at=datetime(2026, 1, 1, 7, tzinfo=UTC),
            weight_kg=70.0,
            body_fat_mass_kg=15.0,
            fat_free_mass_kg=55.0,
            skeletal_muscle_mass_kg=32.0,
            total_body_water_kg=40.0,
            basal_metabolic_rate_kcal=1700,
        )
    )
    await session.commit()
    await _refresh(session)

    response = await client.get("/api/body/composition")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["skeletal_muscle_mass_kg"] == 32.0


async def test_get_tdee_is_invalid_with_too_little_data(
    session: AsyncSession, client: AsyncClient
):
    response = await client.get("/api/analytics/tdee")

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["tdee_kcal"] is None


async def test_get_tdee_estimates_from_intake_and_weight_slope(
    session: AsyncSession, client: AsyncClient
):
    base_day = datetime(2026, 1, 1, 7, tzinfo=UTC)
    for i in range(25):
        session.add(
            NutritionEntry(
                source_uuid=f"tdee-food-{i}",
                consumed_at=base_day + timedelta(days=i),
                food_name="Repas",
                calories=2000.0,
            )
        )
    for i in range(12):
        session.add(
            BodyMeasurement(
                source_uuid=f"tdee-weight-{i}",
                measured_at=base_day + timedelta(days=i * 2),
                weight_kg=80.0 - i * 0.1,
            )
        )
    await session.commit()
    await _refresh(session)

    response = await client.get("/api/analytics/tdee")

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["tdee_kcal"] is not None


async def test_get_energy_balance_needs_bmr_and_intake(
    session: AsyncSession, client: AsyncClient
):
    session.add(
        BodyMeasurement(
            source_uuid="eb-1",
            measured_at=datetime(2026, 1, 1, 7, tzinfo=UTC),
            basal_metabolic_rate_kcal=1700,
        )
    )
    session.add(
        NutritionEntry(
            source_uuid="eb-food-1",
            consumed_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
            food_name="Repas",
            calories=1900.0,
        )
    )
    await session.commit()
    await _refresh(session)

    response = await client.get("/api/analytics/energy-balance")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["balance_kcal"] == pytest.approx(200.0)


async def test_get_resting_hr_averages_per_day(
    session: AsyncSession, client: AsyncClient
):
    session.add(
        Workout(
            source_uuid="rhr-1",
            started_at=datetime(2026, 1, 1, 7, tzinfo=UTC),
            sport="Course",
            resting_hr=55,
        )
    )
    session.add(
        Workout(
            source_uuid="rhr-2",
            started_at=datetime(2026, 1, 1, 18, tzinfo=UTC),
            sport="Course",
            resting_hr=57,
        )
    )
    await session.commit()

    response = await client.get("/api/analytics/resting-hr")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["resting_hr"] == 56


async def test_get_training_load_computes_acute_chronic(
    session: AsyncSession, client: AsyncClient
):
    workout = Workout(
        source_uuid="load-1",
        started_at=datetime(2026, 1, 1, 7, tzinfo=UTC),
        sport="Course",
        resting_hr=55,
        max_hr_custom=190,
        has_samples=True,
    )
    session.add(workout)
    await session.commit()
    await session.refresh(workout)

    base = datetime(2026, 1, 1, 7, tzinfo=UTC)
    for i in range(10):
        session.add(
            WorkoutSample(
                workout_id=workout.id,
                at=base + timedelta(minutes=i),
                heart_rate=150,
            )
        )
    await session.commit()

    response = await client.get("/api/analytics/training-load")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["acute_load"] is not None
