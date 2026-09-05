"""Tests d'intégration de l'API corps, via ASGITransport."""

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.models import BodyMeasurement

pytestmark = pytest.mark.asyncio


async def test_get_measurements_returns_json_with_null_gaps(
    session: AsyncSession,
) -> None:
    session.add(
        BodyMeasurement(
            source_uuid="body-api-1-unique-2099",
            measured_at=datetime(2099, 1, 1, tzinfo=UTC),
            weight_kg=80.0,
        ),
    )
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/body/measurements",
                params={"from": "2099-01-01", "to": "2099-01-31"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body[0]["weight_kg"] == 80.0
    assert body[0]["body_fat_pct"] is None


async def test_get_timeseries_rejects_unknown_metric() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/body/timeseries",
            params={"metrics": "inconnu"},
        )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


async def test_get_timeseries_daily_resolution(session: AsyncSession) -> None:
    session.add(
        BodyMeasurement(
            source_uuid="body-api-2-unique-2099",
            measured_at=datetime(2098, 1, 1, tzinfo=UTC),
            weight_kg=79.0,
        ),
    )
    await session.commit()
    await session.execute(
        __import__("sqlalchemy").text("REFRESH MATERIALIZED VIEW mv_daily_body")
    )
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/body/timeseries",
                params={"metrics": "weight", "resolution": "daily"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "weight" in response.json()


async def test_get_summary_returns_latest_deltas_and_current_phase(
    session: AsyncSession,
) -> None:
    session.add(
        BodyMeasurement(
            source_uuid="body-api-summary-unique-2100",
            measured_at=datetime(2100, 1, 1, tzinfo=UTC),
            weight_kg=75.0,
        ),
    )
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/body/summary", params={"today": "2100-01-01"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["latest"]["weight_kg"] == 75.0
    assert len(body["weight_deltas"]) == 3
    assert {d["window_days"] for d in body["weight_deltas"]} == {7, 30, 90}
