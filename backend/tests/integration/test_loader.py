"""Tests d'idempotence du loader."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.loader import (
    upsert_body_measurements,
    upsert_nutrition_entries,
    upsert_workout_bundle,
)
from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
    SampleRecord,
    StrengthSetRecord,
    WorkoutBundle,
    WorkoutRecord,
)
from app.models import (
    BodyMeasurement,
    NutritionEntry,
    StrengthSet,
    Workout,
    WorkoutSample,
)

UUID = "11111111-1111-1111-1111-111111111111"


async def _count(session: AsyncSession, model: type) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (WorkoutSample, StrengthSet, Workout, BodyMeasurement, NutritionEntry):
        await session.execute(model.__table__.delete())
    await session.commit()


async def test_body_measurement_reimport_updates_instead_of_duplicating(
    session: AsyncSession,
) -> None:
    first = BodyMeasurementRecord(
        source_uuid=UUID,
        measured_at=datetime(2026, 8, 31, 6, 29, tzinfo=UTC),
        weight_kg=65.6,
    )
    await upsert_body_measurements(session, [first])

    corrected = BodyMeasurementRecord(
        source_uuid=UUID,
        measured_at=datetime(2026, 8, 31, 6, 29, tzinfo=UTC),
        weight_kg=66.1,
    )
    await upsert_body_measurements(session, [corrected])

    assert await _count(session, BodyMeasurement) == 1
    stored = (await session.execute(select(BodyMeasurement))).scalar_one()
    assert stored.weight_kg == 66.1


async def test_nutrition_reimport_is_idempotent(session: AsyncSession) -> None:
    record = NutritionEntryRecord(
        source_uuid=UUID,
        consumed_at=datetime(2024, 8, 14, 11, 56, tzinfo=UTC),
        food_name="Oeuf",
        calories=78.0,
    )

    await upsert_nutrition_entries(session, [record])
    await upsert_nutrition_entries(session, [record])

    assert await _count(session, NutritionEntry) == 1


async def test_workout_children_are_replaced_not_appended(
    session: AsyncSession,
) -> None:
    """Réingérer une séance dont les échantillons ont changé ne doit pas
    accumuler les anciens à côté des nouveaux."""
    workout = WorkoutRecord(
        source_uuid=UUID,
        started_at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC),
        sport="Course à pied",
    )
    three = [
        SampleRecord(at=datetime(2026, 2, 5, 19, 2, second, tzinfo=UTC), heart_rate=130)
        for second in (0, 1, 2)
    ]
    await upsert_workout_bundle(session, WorkoutBundle(workout=workout, samples=three))
    assert await _count(session, WorkoutSample) == 3

    one = [SampleRecord(at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC), heart_rate=140)]
    await upsert_workout_bundle(session, WorkoutBundle(workout=workout, samples=one))

    assert await _count(session, Workout) == 1
    assert await _count(session, WorkoutSample) == 1
    stored = (await session.execute(select(WorkoutSample))).scalar_one()
    assert stored.heart_rate == 140


async def test_reingest_without_payloads_preserves_existing_children(
    session: AsyncSession,
) -> None:
    """Régression : Samsung a cessé d'exporter les JSON par séance.

    Un nouvel export référence toujours les séances mais leurs fichiers
    live_data sont absents, donc le paquet arrive sans échantillon. Réingérer
    ne doit PAS détruire ce qui est déjà en base."""
    workout = WorkoutRecord(
        source_uuid=UUID,
        started_at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC),
        sport="Course à pied",
    )
    samples = [
        SampleRecord(at=datetime(2026, 2, 5, 19, 2, second, tzinfo=UTC), heart_rate=130)
        for second in (0, 1, 2)
    ]
    await upsert_workout_bundle(
        session, WorkoutBundle(workout=workout, samples=samples)
    )
    assert await _count(session, WorkoutSample) == 3

    await upsert_workout_bundle(session, WorkoutBundle(workout=workout))

    assert await _count(session, WorkoutSample) == 3
    stored = (await session.execute(select(Workout))).scalar_one()
    assert stored.has_samples is True


async def test_workout_presence_flags_are_computed(session: AsyncSession) -> None:
    workout = WorkoutRecord(
        source_uuid=UUID,
        started_at=datetime(2026, 2, 5, 19, 2, tzinfo=UTC),
        sport="Musculation",
    )
    bundle = WorkoutBundle(
        workout=workout,
        strength_sets=[StrengthSetRecord(idx=0, reps=10, weight_kg=20.0)],
    )

    await upsert_workout_bundle(session, bundle)

    stored = (await session.execute(select(Workout))).scalar_one()
    assert stored.has_strength_sets is True
    assert stored.has_samples is False
    assert stored.has_locations is False
    assert stored.has_swim_lengths is False
