"""Tests d'intégration de l'API nutrition."""

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.models import NutritionEntry

pytestmark = pytest.mark.asyncio


async def test_get_entries_paginates_with_page_param(session: AsyncSession) -> None:
    session.add(
        NutritionEntry(
            source_uuid="nut-api-1-unique-2099",
            consumed_at=datetime(2099, 4, 1, 8, tzinfo=UTC),
            food_name="Riz",
            meal_type=100002,
            unit_code=120001,
            calories=200.0,
        ),
    )
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/nutrition/entries",
                params={"from": "2099-04-01", "to": "2099-04-02", "page": 1},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert any(item["food_name"] == "Riz" for item in body["items"])


async def test_get_daily_endpoint_returns_list() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/nutrition/daily")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
