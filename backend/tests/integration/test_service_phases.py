"""Tests d'intégration du service phases — résolution de la phase courante."""

from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models import Phase, PhaseKind
from app.services.phases import get_current_phase, get_phase, list_phases

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


async def test_get_current_phase_is_none_before_any_phase(session: AsyncSession) -> None:
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
