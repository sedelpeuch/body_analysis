"""Tests d'intégration du service phases — résolution de la phase courante."""

from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError, ValidationError
from app.models import Phase, PhaseKind
from app.schemas.phases import PhaseCreate, PhaseUpdate
from app.services.phases import (
    create_phase,
    delete_phase,
    get_current_phase,
    get_phase,
    list_phases,
    update_phase,
)

pytestmark = pytest.mark.asyncio


async def _reset_phases(session: AsyncSession) -> None:
    await session.execute(delete(Phase))
    await session.commit()


async def _phase(session: AsyncSession, **kwargs) -> Phase:
    phase = Phase(**kwargs)
    session.add(phase)
    await session.commit()
    await session.refresh(phase)
    return phase


async def test_get_current_phase_picks_most_recent_starts_on_at_or_before_today(
    session: AsyncSession,
) -> None:
    """Spec 4.3 : chevauchement d'un jour toléré, la phase courante est
    celle dont starts_on est le plus récent <= aujourd'hui."""
    await _reset_phases(session)
    await _phase(
        session,
        name="Sèche 1",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 3, 1),
    )
    maintain = await _phase(
        session,
        name="Maintien",
        kind=PhaseKind.MAINTAIN,
        starts_on=date(2026, 3, 1),
        ends_on=date(2026, 4, 1),
    )

    result = await get_current_phase(session, today=date(2026, 3, 15))

    assert result.id == maintain.id


async def test_get_current_phase_is_none_before_any_phase(
    session: AsyncSession,
) -> None:
    await _reset_phases(session)
    await _phase(
        session,
        name="Sèche 1",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 3, 1),
    )

    result = await get_current_phase(session, today=date(2025, 12, 1))

    assert result is None


async def test_get_phase_raises_not_found_for_unknown_id(session: AsyncSession) -> None:
    await _reset_phases(session)
    with pytest.raises(NotFoundError):
        await get_phase(session, phase_id=999999)


async def test_list_phases_orders_by_starts_on(session: AsyncSession) -> None:
    await _reset_phases(session)
    await _phase(
        session,
        name="Sèche 2",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 6, 1),
        ends_on=date(2026, 8, 1),
    )
    await _phase(
        session,
        name="Sèche 1",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 3, 1),
    )

    phases = await list_phases(session)

    assert [p.name for p in phases[:2]] == ["Sèche 1", "Sèche 2"]


async def test_create_phase_persists_it(session: AsyncSession) -> None:
    await _reset_phases(session)
    payload = PhaseCreate(
        name="Sèche automne",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 9, 1),
        ends_on=date(2026, 11, 30),
        weight_target_kg=78.0,
    )

    phase = await create_phase(session, payload)

    assert phase.id is not None
    stored = await get_phase(session, phase.id)
    assert stored.name == "Sèche automne"
    assert stored.weight_target_kg == 78.0


async def test_overlapping_phases_are_allowed(session: AsyncSession) -> None:
    """Verrou de non-régression : les données réelles contiennent un
    chevauchement d'un jour entre une sèche et le maintien qui la suit."""
    await _reset_phases(session)
    await create_phase(
        session,
        PhaseCreate(
            name="Sèche",
            kind=PhaseKind.CUT,
            starts_on=date(2026, 6, 1),
            ends_on=date(2026, 9, 1),
        ),
    )

    overlapping = await create_phase(
        session,
        PhaseCreate(
            name="Maintien",
            kind=PhaseKind.MAINTAIN,
            starts_on=date(2026, 9, 1),
            ends_on=date(2026, 10, 1),
        ),
    )

    assert overlapping.id is not None


async def test_update_phase_changes_only_given_fields(session: AsyncSession) -> None:
    await _reset_phases(session)
    phase = await create_phase(
        session,
        PhaseCreate(
            name="Sèche",
            kind=PhaseKind.CUT,
            starts_on=date(2026, 6, 1),
            ends_on=date(2026, 9, 1),
        ),
    )

    updated = await update_phase(
        session, phase.id, PhaseUpdate(daily_calories_target=2200)
    )

    assert updated.daily_calories_target == 2200
    assert updated.name == "Sèche"
    assert updated.starts_on == date(2026, 6, 1)


async def test_update_rejects_ends_on_before_starts_on(session: AsyncSession) -> None:
    await _reset_phases(session)
    phase = await create_phase(
        session,
        PhaseCreate(
            name="Sèche",
            kind=PhaseKind.CUT,
            starts_on=date(2026, 6, 1),
            ends_on=date(2026, 9, 1),
        ),
    )

    with pytest.raises(ValidationError):
        await update_phase(session, phase.id, PhaseUpdate(ends_on=date(2026, 5, 1)))


async def test_update_unknown_phase_raises_not_found(session: AsyncSession) -> None:
    await _reset_phases(session)
    with pytest.raises(NotFoundError):
        await update_phase(session, 999999, PhaseUpdate(name="x"))


async def test_delete_phase_removes_it(session: AsyncSession) -> None:
    await _reset_phases(session)
    phase = await create_phase(
        session,
        PhaseCreate(
            name="Sèche",
            kind=PhaseKind.CUT,
            starts_on=date(2026, 6, 1),
            ends_on=date(2026, 9, 1),
        ),
    )

    await delete_phase(session, phase.id)

    with pytest.raises(NotFoundError):
        await get_phase(session, phase.id)


async def test_delete_unknown_phase_raises_not_found(session: AsyncSession) -> None:
    await _reset_phases(session)
    with pytest.raises(NotFoundError):
        await delete_phase(session, 999999)
