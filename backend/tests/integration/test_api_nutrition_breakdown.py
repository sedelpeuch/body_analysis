"""Test d'intégration de l'endpoint /api/nutrition/breakdown."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_get_breakdown_endpoint_returns_shape() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/nutrition/breakdown")

    assert response.status_code == 200
    body = response.json()
    assert "by_meal_type" in body
    assert "top_foods" in body
