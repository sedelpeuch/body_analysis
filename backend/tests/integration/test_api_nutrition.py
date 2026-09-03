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


async def test_get_eating_window_buckets_by_hour(session: AsyncSession) -> None:
    session.add(
        NutritionEntry(
            source_uuid="nut-window-1-unique-2088",
            consumed_at=datetime(2088, 4, 1, 8, tzinfo=UTC),
            food_name="Café",
            calories=5.0,
        ),
    )
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/nutrition/eating-window",
                params={"from": "2088-04-01", "to": "2088-04-02"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 24
    assert sum(bucket["entry_count"] for bucket in body) == 1


async def test_get_top_foods_ranks_by_frequency(session: AsyncSession) -> None:
    for i in range(3):
        session.add(
            NutritionEntry(
                source_uuid=f"nut-top-{i}-unique-2088",
                consumed_at=datetime(2088, 4, 1, 8, tzinfo=UTC),
                food_name="Riz",
                calories=200.0,
            ),
        )
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/nutrition/top-foods",
                params={"from": "2088-04-01", "to": "2088-04-02", "limit": 5},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body[0]["food_name"] == "Riz"
    assert body[0]["entry_count"] == 3
