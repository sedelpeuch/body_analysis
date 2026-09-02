"""Service CRUD des phases de suivi."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import Phase
from app.schemas.phases import PhaseCreate, PhaseUpdate


async def list_phases(session: AsyncSession) -> list[Phase]:
    query = select(Phase).order_by(Phase.starts_on.desc(), Phase.id.desc())
    return list((await session.execute(query)).scalars().all())


async def get_phase(session: AsyncSession, phase_id: int) -> Phase:
    phase = await session.get(Phase, phase_id)
    if phase is None:
        raise NotFoundError(f"Phase {phase_id} introuvable")
    return phase


async def create_phase(session: AsyncSession, payload: PhaseCreate) -> Phase:
    phase = Phase(
        name=payload.name,
        kind=payload.kind,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        weight_target_kg=payload.weight_target_kg,
        body_fat_target_pct=payload.body_fat_target_pct,
        skeletal_muscle_target_kg=payload.skeletal_muscle_target_kg,
        daily_calories_target=payload.daily_calories_target,
        notes=payload.notes,
    )
    session.add(phase)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ConflictError("Phase déjà existante ou conflit de données.") from error
    await session.refresh(phase)
    return phase


async def update_phase(
    session: AsyncSession, phase_id: int, payload: PhaseUpdate
) -> Phase:
    phase = await get_phase(session, phase_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(phase, field_name, value)

    starts_on = phase.starts_on
    ends_on = phase.ends_on
    if ends_on < starts_on:
        raise ValidationError("ends_on doit être postérieure ou égale à starts_on")

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ConflictError("La mise à jour de phase est en conflit avec les données.") from error
    await session.refresh(phase)
    return phase


async def delete_phase(session: AsyncSession, phase_id: int) -> None:
    phase = await get_phase(session, phase_id)
    await session.delete(phase)
    await session.commit()
