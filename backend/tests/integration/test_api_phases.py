"""Tests d'intégration de l'API phases (lecture seule)."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.models import Phase, PhaseKind

pytestmark = pytest.mark.asyncio


async def test_get_phase_returns_404_problem_json_when_missing() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/phases/999999")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


async def test_get_phase_by_id_returns_kind_and_targets(session: AsyncSession) -> None:
    phase = Phase(
        name="Sèche test",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 3, 1),
        weight_target_kg=75.0,
    )
    session.add(phase)
    await session.commit()
    await session.refresh(phase)

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/phases/{phase.id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "cut"
    assert body["weight_target_kg"] == 75.0


async def test_get_current_phase_can_be_null(session: AsyncSession) -> None:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/phases/current", params={"today": "1999-01-01"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() is None
