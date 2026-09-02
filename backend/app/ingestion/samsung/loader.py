"""Écriture idempotente des dataclasses de domaine en base.

Toute insertion passe par ON CONFLICT DO UPDATE sur source_uuid. Les tables
filles d'une séance sont remplacées et non complétées : réingérer une séance
dont les échantillons ont changé ne doit pas accumuler les anciens.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import delete, exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.records import (
    BodyMeasurementRecord,
    NutritionEntryRecord,
    PhaseRecord,
    WorkoutBundle,
)
from app.models import (
    BodyMeasurement,
    Phase,
    StrengthSet,
    SwimLength,
    Workout,
    WorkoutExtra,
    WorkoutLocation,
    WorkoutSample,
)
from app.models.nutrition import NutritionEntry

BATCH_SIZE = 1000


def _batches(items: Sequence[Any], size: int = BATCH_SIZE) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def _upsert_on_source_uuid(
    session: AsyncSession, model: type, records: Sequence[Any]
) -> int:
    if not records:
        return 0
    total = 0
    for batch in _batches(records):
        values = [dataclasses.asdict(record) for record in batch]
        statement = insert(model).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=["source_uuid"],
            set_={
                key: statement.excluded[key]
                for key in values[0]
                if key != "source_uuid"
            },
        )
        await session.execute(statement)
        total += len(batch)
    await session.commit()
    return total


async def upsert_body_measurements(
    session: AsyncSession, records: Sequence[BodyMeasurementRecord]
) -> int:
    return await _upsert_on_source_uuid(session, BodyMeasurement, records)


async def upsert_nutrition_entries(
    session: AsyncSession, records: Sequence[NutritionEntryRecord]
) -> int:
    return await _upsert_on_source_uuid(session, NutritionEntry, records)


async def upsert_phases(session: AsyncSession, records: Sequence[PhaseRecord]) -> int:
    """Les phases n'ont pas de source_uuid : la clé naturelle est le nom et
    la date de début. Le remplacement complet est plus simple et sans risque,
    il n'y en a que huit."""
    if not records:
        return 0
    await session.execute(delete(Phase))
    await session.execute(
        insert(Phase).values([dataclasses.asdict(record) for record in records])
    )
    await session.commit()
    return len(records)


async def upsert_workout_bundle(session: AsyncSession, bundle: WorkoutBundle) -> int:
    # Les drapeaux has_* ne figurent PAS ici : ils sont recalculés depuis la
    # base après l'écriture des lignes filles, sinon un export sans JSON les
    # remettrait à faux alors que les données restent présentes.
    values = dataclasses.asdict(bundle.workout)

    statement = insert(Workout).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=["source_uuid"],
        set_={key: statement.excluded[key] for key in values if key != "source_uuid"},
    ).returning(Workout.id)
    workout_id = (await session.execute(statement)).scalar_one()

    children = (
        (WorkoutSample, bundle.samples),
        (WorkoutLocation, bundle.locations),
        (SwimLength, bundle.swim_lengths),
        (StrengthSet, bundle.strength_sets),
        (WorkoutExtra, bundle.extras),
    )
    for model, records in children:
        if not records:
            # L'export courant n'apporte rien pour ce type : on PRÉSERVE
            # l'existant. Samsung a cessé d'exporter les JSON par séance ;
            # un remplacement inconditionnel détruirait les 2,8 M
            # d'échantillons déjà en base au premier import d'un nouvel
            # export.
            continue
        await session.execute(delete(model).where(model.workout_id == workout_id))
        rows = [
            {"workout_id": workout_id, **dataclasses.asdict(record)}
            for record in records
        ]
        for batch in _batches(rows):
            await session.execute(insert(model).values(list(batch)))

    await _refresh_presence_flags(session, workout_id)
    return workout_id


async def _refresh_presence_flags(session: AsyncSession, workout_id: int) -> None:
    """Recalcule les drapeaux depuis la base, jamais depuis le paquet.

    Les lignes filles peuvent préexister sans être dans le paquet courant ;
    déduire les drapeaux du seul paquet les remettrait à faux alors que les
    données sont bien là.
    """
    flags = {}
    for column, model in (
        ("has_samples", WorkoutSample),
        ("has_locations", WorkoutLocation),
        ("has_swim_lengths", SwimLength),
        ("has_strength_sets", StrengthSet),
    ):
        present = await session.scalar(
            select(exists().where(model.workout_id == workout_id))
        )
        flags[column] = bool(present)
    await session.execute(
        update(Workout).where(Workout.id == workout_id).values(**flags)
    )


async def upsert_workout_bundles(
    session: AsyncSession, bundles: Iterable[WorkoutBundle]
) -> int:
    """Commite tous les 100 paquets : garder 4 734 séances et leurs 2,8 M
    d'échantillons dans une seule transaction ferait exploser la mémoire."""
    total = 0
    for bundle in bundles:
        await upsert_workout_bundle(session, bundle)
        total += 1
        if total % 100 == 0:
            await session.commit()
    await session.commit()
    return total
