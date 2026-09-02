"""Tests du pipeline d'ingestion de bout en bout."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.pipeline import discover_source, run_ingestion
from app.models import (
    BodyMeasurement,
    IngestionRun,
    IngestionStatus,
    NutritionEntry,
    Phase,
    Workout,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def export_dir(tmp_path: Path) -> Path:
    """Construit un export minimal mais complet dans un répertoire jetable."""
    shutil.copy(
        FIXTURES / "samsung" / "weight_sample.csv",
        tmp_path / "com.samsung.health.weight.20260831162666.csv",
    )
    shutil.copy(FIXTURES / "phases.json", tmp_path / "phases.json")
    return tmp_path


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession) -> None:
    for model in (Workout, BodyMeasurement, NutritionEntry, Phase, IngestionRun):
        await session.execute(model.__table__.delete())
    await session.commit()


async def _count(session: AsyncSession, model: type) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_run_ingests_and_records_success(
    session: AsyncSession, export_dir: Path
) -> None:
    run = await run_ingestion(
        session,
        discover_source(export_dir),
        kind="test",
        source_name="fixture",
    )

    assert run.status is IngestionStatus.SUCCESS
    assert run.finished_at is not None
    assert run.counts["body_measurements"] == 2
    assert run.counts["phases"] == 3
    assert await _count(session, BodyMeasurement) == 2
    assert await _count(session, Phase) == 3


async def test_second_run_creates_no_duplicates(
    session: AsyncSession, export_dir: Path
) -> None:
    """L'assertion centrale de tout ce plan."""
    source = discover_source(export_dir)

    await run_ingestion(session, source, kind="test", source_name="fixture")
    await run_ingestion(session, source, kind="test", source_name="fixture")

    assert await _count(session, BodyMeasurement) == 2
    assert await _count(session, Phase) == 3
    assert await _count(session, IngestionRun) == 2


async def test_failed_run_is_recorded_with_its_error(
    session: AsyncSession, tmp_path: Path
) -> None:
    broken = tmp_path / "com.samsung.health.weight.20260831162666.csv"
    broken.write_bytes(b"\xff\xfe pas de l'utf-8 valide")

    with pytest.raises(UnicodeError):
        await run_ingestion(
            session,
            discover_source(tmp_path),
            kind="test",
            source_name="cassé",
        )

    run = (await session.execute(select(IngestionRun))).scalars().one()
    assert run.status is IngestionStatus.FAILED
    assert run.error
