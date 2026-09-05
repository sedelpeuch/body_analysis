"""Tests d'intégration de l'API phases."""

from datetime import UTC, date, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.models import BodyMeasurement, Phase, PhaseKind

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
                "/api/phases/current",
                params={"today": "1999-01-01"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() is None


_PAYLOAD = {
    "name": "Sèche automne",
    "kind": "cut",
    "starts_on": "2026-09-01",
    "ends_on": "2026-11-30",
    "weight_target_kg": 78.0,
}


async def test_post_phase_returns_201(session: AsyncSession) -> None:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/phases", json=_PAYLOAD)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sèche automne"
    assert body["kind"] == "cut"


async def test_post_phase_with_invalid_dates_is_422_problem_json(
    session: AsyncSession,
) -> None:
    invalid = {**_PAYLOAD, "starts_on": "2026-11-30", "ends_on": "2026-09-01"}

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/phases", json=invalid)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_post_phase_with_invalid_kind_is_422(session: AsyncSession) -> None:
    invalid = {**_PAYLOAD, "kind": "shred"}

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/phases", json=invalid)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


async def test_patch_phase_updates_a_single_field(session: AsyncSession) -> None:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = (await client.post("/api/phases", json=_PAYLOAD)).json()
            response = await client.patch(
                f"/api/phases/{created['id']}", json={"daily_calories_target": 2100}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["daily_calories_target"] == 2100
    assert response.json()["name"] == "Sèche automne"


async def test_patch_phase_with_invalid_dates_is_422(session: AsyncSession) -> None:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = (await client.post("/api/phases", json=_PAYLOAD)).json()
            response = await client.patch(
                f"/api/phases/{created['id']}", json={"ends_on": "2020-01-01"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


async def test_patch_unknown_phase_is_404_problem_json(session: AsyncSession) -> None:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch("/api/phases/999999", json={"name": "x"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_delete_phase_returns_204(session: AsyncSession) -> None:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = (await client.post("/api/phases", json=_PAYLOAD)).json()
            response = await client.delete(f"/api/phases/{created['id']}")
            listing = await client.get("/api/phases")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert created["id"] not in [p["id"] for p in listing.json()]


async def test_delete_unknown_phase_is_404_problem_json(session: AsyncSession) -> None:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/phases/999999")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_get_transverse_report_ranks_success_rate_per_metric(
    session: AsyncSession,
) -> None:
    achieved = Phase(
        name="Sèche réussie",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 2, 1),
        weight_target_kg=1.0,
    )
    session.add(achieved)
    session.add(
        BodyMeasurement(
            source_uuid="body-transverse-report-1",
            measured_at=datetime(2026, 1, 1, tzinfo=UTC),
            weight_kg=90.0,
        ),
    )
    session.add(
        BodyMeasurement(
            source_uuid="body-transverse-report-2",
            measured_at=datetime(2026, 2, 1, tzinfo=UTC),
            weight_kg=1.0,
        ),
    )
    await session.commit()

    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/phases/report", params={"today": "2026-02-01"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    rates = {r["metric"]: r for r in response.json()}
    assert rates["weight"]["achieved_count"] >= 1
