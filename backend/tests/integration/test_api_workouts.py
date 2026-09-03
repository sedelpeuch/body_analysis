"""Tests d'intégration des endpoints /api/workouts et /api/sports."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.models import StrengthSet, SwimLength, Workout, WorkoutLocation, WorkoutSample

pytestmark = pytest.mark.asyncio


async def _clean(session: AsyncSession) -> None:
    for model in (WorkoutSample, WorkoutLocation, SwimLength, StrengthSet, Workout):
        await session.execute(model.__table__.delete())
    await session.commit()


async def _make_workout(session: AsyncSession, **overrides) -> Workout:
    defaults = dict(
        source_uuid=f"wk-{overrides.get('id', 'a')}-{overrides.get('sport', 'x')}",
        started_at=datetime(2026, 1, 1, 8, tzinfo=UTC),
        ended_at=datetime(2026, 1, 1, 9, tzinfo=UTC),
        duration_ms=3_600_000,
        sport="Course",
        sport_type=1002,
        distance_m=10_000.0,
        calories_kcal=600.0,
        mean_heart_rate=140.0,
        max_hr_custom=190,
        has_samples=False,
        has_locations=False,
        has_swim_lengths=False,
        has_strength_sets=False,
    )
    defaults.update(overrides)
    workout = Workout(**defaults)
    session.add(workout)
    await session.commit()
    await session.refresh(workout)
    return workout


@pytest.fixture
async def client(session: AsyncSession):
    await _clean(session)
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as opened:
            yield opened
    finally:
        app.dependency_overrides.clear()


async def test_list_sports_counts_workouts(session: AsyncSession, client: AsyncClient):
    await _make_workout(session, source_uuid="s1", sport="Course")
    await _make_workout(session, source_uuid="s2", sport="Course")
    await _make_workout(session, source_uuid="s3", sport="Natation")

    response = await client.get("/api/sports")

    assert response.status_code == 200
    body = {row["sport"]: row["workout_count"] for row in response.json()}
    assert body["Course"] == 2
    assert body["Natation"] == 1


async def test_list_workouts_paginates_with_cursor(
    session: AsyncSession, client: AsyncClient
):
    for i in range(3):
        await _make_workout(
            session,
            source_uuid=f"list-{i}",
            started_at=datetime(2026, 1, 1 + i, 8, tzinfo=UTC),
        )

    first_page = await client.get("/api/workouts", params={"limit": 2})
    assert first_page.status_code == 200
    body = first_page.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None

    second_page = await client.get(
        "/api/workouts", params={"limit": 2, "cursor": body["next_cursor"]}
    )
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["next_cursor"] is None


async def test_get_workout_returns_detail(session: AsyncSession, client: AsyncClient):
    workout = await _make_workout(session, source_uuid="detail-1")

    response = await client.get(f"/api/workouts/{workout.id}")

    assert response.status_code == 200
    assert response.json()["sport"] == "Course"


async def test_get_unknown_workout_is_404_problem_json(client: AsyncClient):
    response = await client.get("/api/workouts/999999")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


async def test_get_samples_decimates_via_width_bucket(
    session: AsyncSession, client: AsyncClient
):
    workout = await _make_workout(session, source_uuid="samples-1")
    base = datetime(2026, 1, 1, 8, tzinfo=UTC)
    for i in range(20):
        session.add(
            WorkoutSample(
                workout_id=workout.id,
                at=base + timedelta(seconds=i),
                heart_rate=120 + i,
                speed_mps=3.0,
                distance_m=float(i * 3),
                cadence=80,
            )
        )
    await session.commit()

    response = await client.get(
        f"/api/workouts/{workout.id}/samples", params={"points": 5}
    )

    assert response.status_code == 200
    points = response.json()
    assert 1 <= len(points) <= 5
    assert points[0]["heart_rate"] is not None


async def test_get_track_returns_geojson_linestring(
    session: AsyncSession, client: AsyncClient
):
    workout = await _make_workout(session, source_uuid="track-1")
    base = datetime(2026, 1, 1, 8, tzinfo=UTC)
    for i in range(3):
        session.add(
            WorkoutLocation(
                workout_id=workout.id,
                at=base + timedelta(seconds=i),
                latitude=48.85 + i * 0.001,
                longitude=2.35 + i * 0.001,
            )
        )
    await session.commit()

    response = await client.get(f"/api/workouts/{workout.id}/track")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "LineString"
    assert len(body["coordinates"]) == 3
    assert body["coordinates"][0] == [2.35, 48.85]


async def test_get_splits_returns_per_km_splits(
    session: AsyncSession, client: AsyncClient
):
    workout = await _make_workout(session, source_uuid="splits-1")
    base = datetime(2026, 1, 1, 8, tzinfo=UTC)
    for i in range(5):
        session.add(
            WorkoutSample(
                workout_id=workout.id,
                at=base + timedelta(minutes=i),
                heart_rate=140,
                distance_m=float(i * 300),
            )
        )
    await session.commit()

    response = await client.get(f"/api/workouts/{workout.id}/splits")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_get_hr_zones_requires_max_hr(session: AsyncSession, client: AsyncClient):
    workout = await _make_workout(
        session, source_uuid="hr-1", max_hr_custom=None, resting_hr=None
    )

    response = await client.get(f"/api/workouts/{workout.id}/hr-zones")

    assert response.status_code == 422


async def test_get_hr_zones_returns_zone_times(
    session: AsyncSession, client: AsyncClient
):
    workout = await _make_workout(session, source_uuid="hr-2", max_hr_custom=190)
    base = datetime(2026, 1, 1, 8, tzinfo=UTC)
    for i in range(3):
        session.add(
            WorkoutSample(
                workout_id=workout.id,
                at=base + timedelta(minutes=i),
                heart_rate=150,
            )
        )
    await session.commit()

    response = await client.get(f"/api/workouts/{workout.id}/hr-zones")

    assert response.status_code == 200
    assert len(response.json()) == 5


async def test_get_swim_aggregates_swolf(session: AsyncSession, client: AsyncClient):
    workout = await _make_workout(session, source_uuid="swim-1", sport="Natation")
    session.add(
        SwimLength(
            workout_id=workout.id,
            idx=0,
            duration_ms=30_000,
            stroke_count=20,
            stroke_type="Crawl",
        )
    )
    await session.commit()

    response = await client.get(f"/api/workouts/{workout.id}/swim")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["stroke_type"] == "Crawl"
    assert body[0]["mean_swolf"] == 50.0


async def test_get_strength_returns_sets_and_volume(
    session: AsyncSession, client: AsyncClient
):
    workout = await _make_workout(
        session, source_uuid="strength-1", sport="Musculation"
    )
    session.add(
        StrengthSet(workout_id=workout.id, idx=0, reps=10, weight_kg=50.0)
    )
    await session.commit()

    response = await client.get(f"/api/workouts/{workout.id}/strength")

    assert response.status_code == 200
    body = response.json()
    assert body["set_count"] == 1
    assert body["total_volume_kg"] == 500.0


async def test_get_stats_aggregates_across_workouts(
    session: AsyncSession, client: AsyncClient
):
    await _make_workout(session, source_uuid="stats-1", distance_m=1000.0)
    await _make_workout(session, source_uuid="stats-2", distance_m=2000.0)

    response = await client.get("/api/workouts/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["session_count"] == 2
    assert body["total_distance_m"] == 3000.0


async def test_get_records_finds_the_best_per_category(
    session: AsyncSession, client: AsyncClient
):
    await _make_workout(session, source_uuid="rec-1", distance_m=5000.0)
    await _make_workout(session, source_uuid="rec-2", distance_m=15000.0)

    response = await client.get("/api/workouts/records")

    assert response.status_code == 200
    labels = {r["label"]: r["value"] for r in response.json()}
    assert labels["Distance la plus longue"] == 15000.0


async def test_get_calendar_filters_by_year(session: AsyncSession, client: AsyncClient):
    from sqlalchemy import text

    await _make_workout(
        session, source_uuid="cal-1", started_at=datetime(2026, 3, 1, 8, tzinfo=UTC)
    )
    await session.execute(text("REFRESH MATERIALIZED VIEW mv_daily_training"))
    await session.commit()

    response = await client.get("/api/workouts/calendar", params={"year": 2026})

    assert response.status_code == 200
    assert len(response.json()) == 1
