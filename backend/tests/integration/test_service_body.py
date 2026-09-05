"""Tests d'intégration du service corps, contre PostgreSQL jetable."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DateRange
from app.models import BodyMeasurement
from app.services.body import get_timeseries, list_measurements

pytestmark = pytest.mark.asyncio


async def _insert_measurement(
    session: AsyncSession,
    *,
    source_uuid: str,
    at: datetime,
    weight_kg: float | None,
) -> None:
    session.add(
        BodyMeasurement(source_uuid=source_uuid, measured_at=at, weight_kg=weight_kg),
    )
    await session.commit()


async def test_list_measurements_filters_by_date_range(session: AsyncSession) -> None:
    await _insert_measurement(
        session,
        source_uuid="body-1-unique-2099",
        at=datetime(2099, 1, 1, tzinfo=UTC),
        weight_kg=80.0,
    )
    await _insert_measurement(
        session,
        source_uuid="body-2-unique-2099",
        at=datetime(2099, 6, 1, tzinfo=UTC),
        weight_kg=75.0,
    )

    result = await list_measurements(
        session,
        DateRange(start=date(2099, 1, 1), end=date(2099, 2, 1)),
    )

    assert [r.weight_kg for r in result] == [80.0]


async def test_list_measurements_preserves_null_body_fat(session: AsyncSession) -> None:
    await _insert_measurement(
        session,
        source_uuid="body-3-unique-2099",
        at=datetime(2098, 1, 5, tzinfo=UTC),
        weight_kg=80.0,
    )

    result = await list_measurements(
        session,
        DateRange(start=date(2098, 1, 1), end=date(2098, 1, 31)),
    )

    assert result[0].body_fat_pct is None


async def test_get_timeseries_raw_resolution_returns_selected_metrics(
    session: AsyncSession,
) -> None:
    await _insert_measurement(
        session,
        source_uuid="body-4-unique-2099",
        at=datetime(2097, 1, 1, tzinfo=UTC),
        weight_kg=80.0,
    )

    result = await get_timeseries(
        session,
        DateRange(start=date(2097, 1, 1), end=date(2097, 1, 31)),
        metrics=["weight"],
        resolution="raw",
    )

    assert "weight" in result
    assert result["weight"][0].value == 80.0
