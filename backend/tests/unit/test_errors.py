"""Vérifie la traduction des erreurs en application/problem+json (RFC 9457)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import (
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    ValidationError,
    register_error_handlers,
)

PROBLEM_MEDIA_TYPE = "application/problem+json"


class _Body(BaseModel):
    name: str


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/not-found")
    async def not_found() -> None:
        raise NotFoundError("Phase 42 introuvable")

    @app.get("/conflict")
    async def conflict() -> None:
        raise ConflictError("sha256 déjà utilisé", sha256="abc")

    @app.get("/validation")
    async def validation() -> None:
        raise ValidationError("ends_on doit être postérieure à starts_on")

    @app.get("/unsupported")
    async def unsupported() -> None:
        raise UnsupportedMediaTypeError("Type non reconnu", allowed=["image/jpeg"])

    @app.get("/too-large")
    async def too_large() -> None:
        raise PayloadTooLargeError("Fichier trop volumineux")

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("panne imprévue")

    @app.post("/echo")
    async def echo(body: _Body) -> dict[str, str]:
        return {"name": body.name}

    return app


def _client() -> TestClient:
    return TestClient(_build_app(), raise_server_exceptions=False)


def test_domain_error_is_problem_json() -> None:
    response = _client().get("/not-found")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert body["status"] == 404
    assert body["title"] == "Ressource introuvable"
    assert body["detail"] == "Phase 42 introuvable"
    assert body["instance"] == "/not-found"


def test_domain_error_extra_fields_are_included() -> None:
    body = _client().get("/conflict").json()

    assert body["status"] == 409
    assert body["sha256"] == "abc"


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/validation", 422),
        ("/unsupported", 415),
        ("/too-large", 413),
    ],
)
def test_every_domain_error_maps_to_its_status(path: str, status: int) -> None:
    response = _client().get(path)

    assert response.status_code == status
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)


def test_pydantic_validation_error_is_problem_json() -> None:
    """Le handler par défaut de FastAPI renvoie du JSON simple ; RFC 9457
    exige application/problem+json même pour les erreurs de schéma."""
    response = _client().post("/echo", json={"name": 123, "extra": "trop"})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert body["title"] == "Requête invalide"
    assert isinstance(body["errors"], list)
    assert body["errors"]


def test_missing_route_is_problem_json() -> None:
    """Un 404 de routage Starlette doit lui aussi être traduit."""
    response = _client().get("/route-inexistante")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)


def test_unhandled_exception_is_problem_json_and_does_not_leak_details() -> None:
    response = _client().get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert "panne imprévue" not in body["detail"]
