"""Tests d'intégration du service d'import ZIP."""

import zipfile
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import ValidationError
from app.models import IngestionRun, IngestionStatus
from app.services.imports import (
    create_pending_run,
    run_zip_import,
    validate_zip_signature,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(IngestionRun.__table__.delete())
    await session.commit()
    yield


def _zip_of(tmp_path: Path, name: str, contents: dict[str, bytes]) -> Path:
    zip_path = tmp_path / name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry_name, data in contents.items():
            archive.writestr(entry_name, data)
    return zip_path


async def test_create_pending_run_is_immediately_visible(session: AsyncSession) -> None:
    run = await create_pending_run(session, source_name="export.zip")

    assert run.id is not None
    assert run.status is IngestionStatus.RUNNING
    stored = (await session.execute(select(IngestionRun))).scalar_one()
    assert stored.id == run.id


def test_validate_zip_signature_accepts_a_real_zip_header() -> None:
    validate_zip_signature(b"PK\x03\x04reste-des-octets")


def test_validate_zip_signature_rejects_anything_else() -> None:
    with pytest.raises(ValidationError):
        validate_zip_signature(b"ceci n'est pas un zip")


async def test_run_zip_import_extracts_and_completes_the_run(
    session: AsyncSession, tmp_path: Path, engine
) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    zip_path = _zip_of(
        tmp_path,
        "export.zip",
        {"com.samsung.health.weight.20260831162666.csv": weight_csv},
    )
    run = await create_pending_run(session, source_name="export.zip")
    await session.commit()

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    await run_zip_import(factory, run_id=run.id, zip_path=zip_path)

    async with factory() as verification_session:
        completed = await verification_session.get(IngestionRun, run.id)
        assert completed.status is IngestionStatus.SUCCESS
        assert completed.counts["body_measurements"] == 2

    assert not zip_path.exists()  # nettoyé après usage


async def test_run_zip_import_marks_the_run_failed_on_a_malicious_archive(
    session: AsyncSession, tmp_path: Path, engine
) -> None:
    zip_path = _zip_of(tmp_path, "evil.zip", {"../evil.txt": b"charge utile"})
    run = await create_pending_run(session, source_name="evil.zip")
    await session.commit()

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    with pytest.raises(ValidationError):
        await run_zip_import(factory, run_id=run.id, zip_path=zip_path)

    async with factory() as verification_session:
        failed = await verification_session.get(IngestionRun, run.id)
        assert failed.status is IngestionStatus.FAILED
        assert "sort du" in failed.error
