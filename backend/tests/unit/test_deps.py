"""Tests des dépendances communes aux routers de lecture."""

from datetime import date

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import DateRange, date_range


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/range")
    async def endpoint(r: DateRange = Depends(date_range)) -> dict[str, str | None]:
        return {
            "start": r.start.isoformat() if r.start else None,
            "end": r.end.isoformat() if r.end else None,
        }

    return app


def test_date_range_parses_from_and_to() -> None:
    client = TestClient(_build_app())

    response = client.get("/range", params={"from": "2026-01-01", "to": "2026-01-31"})

    assert response.status_code == 200
    assert response.json() == {"start": "2026-01-01", "end": "2026-01-31"}


def test_date_range_defaults_to_none() -> None:
    client = TestClient(_build_app())

    response = client.get("/range")

    assert response.json() == {"start": None, "end": None}


def test_date_range_dataclass_fields() -> None:
    r = DateRange(start=date(2026, 1, 1), end=None)

    assert r.start == date(2026, 1, 1)
    assert r.end is None
