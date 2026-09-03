"""Vérifie que run_ingestion peut reprendre un IngestionRun déjà créé,
sans quoi l'import HTTP ne pourrait pas donner un identifiant au front avant
que l'ingestion, potentiellement longue, ne démarre."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.pipeline import discover_source, run_ingestion
from app.models import IngestionRun, IngestionStatus

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def export_dir(tmp_path: Path) -> Path:
    shutil.copy(
        FIXTURES / "samsung" / "weight_sample.csv",
        tmp_path / "com.samsung.health.weight.20260831162666.csv",
    )
    return tmp_path


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(IngestionRun.__table__.delete())
    await session.commit()
    yield


async def test_run_ingestion_reuses_a_preexisting_run(
    session: AsyncSession, export_dir: Path
) -> None:
    preexisting = IngestionRun(
        kind="samsung_zip", source_name="export.zip", status=IngestionStatus.RUNNING
    )
    session.add(preexisting)
    await session.commit()
    await session.refresh(preexisting)

    result = await run_ingestion(
        session,
        discover_source(export_dir),
        kind="samsung_zip",
        source_name="export.zip",
        run=preexisting,
    )

    assert result.id == preexisting.id
    assert result.status is IngestionStatus.SUCCESS
    rows = (await session.execute(select(IngestionRun))).scalars().all()
    assert len(rows) == 1  # aucune ligne créée en plus de celle réutilisée


async def test_run_ingestion_without_run_still_creates_one(
    session: AsyncSession, export_dir: Path
) -> None:
    """Non-régression : le script de migration jetable appelle
    run_ingestion sans l'argument run et doit continuer à fonctionner."""
    result = await run_ingestion(
        session, discover_source(export_dir), kind="migration", source_name="fixture"
    )

    assert result.id is not None
    assert result.status is IngestionStatus.SUCCESS
