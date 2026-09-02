"""Vérifie que les exceptions de domaine deviennent du problem+json."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.problem import register_exception_handlers
from app.errors import NotFoundError, ValidationError


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/not-found")
    async def not_found() -> None:
        raise NotFoundError("séance 42 introuvable")

    @app.get("/boom/invalid")
    async def invalid() -> None:
        raise ValidationError("points doit être entre 1 et 5000")

    return app


def test_domain_error_becomes_problem_json() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/not-found")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["title"] == "Ressource introuvable"
    assert body["status"] == 404
    assert body["detail"] == "séance 42 introuvable"


def test_validation_error_is_422() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/invalid")

    assert response.status_code == 422
    assert response.json()["detail"] == "points doit être entre 1 et 5000"


def test_request_validation_error_is_also_problem_json() -> None:
    """Une requête mal formée (query param invalide) doit aussi produire du
    problem+json, pas le format d'erreur par défaut de FastAPI."""
    app = _build_app()

    @app.get("/boom/query")
    async def with_query(points: int) -> dict[str, int]:
        return {"points": points}

    client = TestClient(app)
    response = client.get("/boom/query", params={"points": "pas-un-entier"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Paramètres invalides"
