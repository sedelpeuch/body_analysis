"""Test d'intégration de l'endpoint /api/phases/{id}/report."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.models import Phase, PhaseKind

pytestmark = pytest.mark.asyncio


async def test_get_phase_report_endpoint(session: AsyncSession) -> None:
    phase = Phase(
        name="Sèche report api",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 2, 1),
    )
    session.add(phase)
    await session.commit()
    await session.refresh(phase)

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/phases/{phase.id}/report")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["metrics"]) == 3
    assert {m["metric"] for m in body["metrics"]} == {"weight", "body_fat", "muscle"}
