"""Tests d'intégration du rapport de phase — assemble deltas, composition
et objectifs autour de mesures et d'un journal alimentaire réels."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.objectives import Metric
from app.models import BodyMeasurement, NutritionEntry, Phase, PhaseKind
from app.services.phases import get_phase_report

pytestmark = pytest.mark.asyncio


async def test_get_phase_report_computes_metrics_and_objective_status(
    session: AsyncSession,
) -> None:
    phase = Phase(
        name="Sèche rapport",
        kind=PhaseKind.CUT,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 3, 2),
        weight_target_kg=77.0,
    )
    session.add(phase)
    session.add_all(
        [
            BodyMeasurement(
                source_uuid="rpt-1",
                measured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                weight_kg=80.0,
                body_fat_pct=25.0,
                body_fat_mass_kg=22.0,
                skeletal_muscle_mass_kg=50.0,
                fat_free_mass_kg=60.0,
            ),
            BodyMeasurement(
                source_uuid="rpt-2",
                measured_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                weight_kg=78.0,
                body_fat_pct=22.0,
                body_fat_mass_kg=19.0,
                skeletal_muscle_mass_kg=52.0,
                fat_free_mass_kg=62.0,
            ),
            NutritionEntry(
                source_uuid="rpt-3",
                consumed_at=datetime(2026, 1, 15, 12, tzinfo=timezone.utc),
                food_name="Repas",
                calories=2200.0,
            ),
            NutritionEntry(
                source_uuid="rpt-4",
                consumed_at=datetime(2026, 2, 15, 12, tzinfo=timezone.utc),
                food_name="Repas",
                calories=2400.0,
            ),
        ]
    )
    await session.commit()
    await session.refresh(phase)
    await session.execute(text("REFRESH MATERIALIZED VIEW mv_daily_nutrition"))
    await session.commit()

    report = await get_phase_report(session, phase.id, today=date(2026, 3, 2))

    weight_metric = next(m for m in report.metrics if m.metric is Metric.WEIGHT)
    assert weight_metric.start_value == 80.0
    assert weight_metric.end_value == 78.0
    assert weight_metric.change == pytest.approx(-2.0)
    assert weight_metric.objective is not None
    assert weight_metric.objective.achieved is False
    assert report.average_calories_kcal == pytest.approx(2300.0)
