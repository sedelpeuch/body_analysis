"""Tests d'intégration des endpoints /api/imports."""

import io
import zipfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import get_session, get_session_factory
from app.main import create_app
from app.models import IngestionRun

FIXTURES = Path(__file__).parents[1] / "fixtures"


def _zip_bytes(contents: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    return buffer.getvalue()


@pytest.fixture
async def client(
    session: AsyncSession, test_session_factory: async_sessionmaker[AsyncSession]
):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_session_factory] = lambda: test_session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as opened:
        yield opened


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(IngestionRun.__table__.delete())
    await session.commit()
    yield


async def test_post_samsung_zip_returns_202_with_a_pollable_id(
    client: AsyncClient,
) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    archive = _zip_bytes({"com.samsung.health.weight.20260831162666.csv": weight_csv})

    response = await client.post(
        "/api/imports/samsung-zip",
        files={"file": ("export.zip", archive, "application/zip")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["id"] is not None
    assert body["status"] in ("running", "success")


async def test_import_completes_and_is_reflected_by_get(client: AsyncClient) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    archive = _zip_bytes({"com.samsung.health.weight.20260831162666.csv": weight_csv})

    created = (
        await client.post(
            "/api/imports/samsung-zip",
            files={"file": ("export.zip", archive, "application/zip")},
        )
    ).json()

    response = await client.get(f"/api/imports/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["counts"]["body_measurements"] == 2


async def test_post_a_non_zip_file_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/imports/samsung-zip",
        files={"file": ("export.zip", b"pas un zip", "application/zip")},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_post_a_malicious_zip_ends_up_failed(client: AsyncClient) -> None:
    archive = _zip_bytes({"../evil.txt": b"charge utile"})

    created = (
        await client.post(
            "/api/imports/samsung-zip",
            files={"file": ("evil.zip", archive, "application/zip")},
        )
    ).json()

    response = await client.get(f"/api/imports/{created['id']}")

    assert response.json()["status"] == "failed"
    assert "sort du" in response.json()["error"]


async def test_get_imports_lists_every_run(client: AsyncClient) -> None:
    weight_csv = (FIXTURES / "samsung" / "weight_sample.csv").read_bytes()
    archive = _zip_bytes({"com.samsung.health.weight.20260831162666.csv": weight_csv})
    await client.post(
        "/api/imports/samsung-zip",
        files={"file": ("a.zip", archive, "application/zip")},
    )
    await client.post(
        "/api/imports/samsung-zip",
        files={"file": ("b.zip", archive, "application/zip")},
    )

    response = await client.get("/api/imports")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_unknown_import_is_404_problem_json(client: AsyncClient) -> None:
    response = await client.get("/api/imports/999999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
