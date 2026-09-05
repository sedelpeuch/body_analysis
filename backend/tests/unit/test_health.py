"""Vérifie que l'application se construit et répond."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_core_routes_are_registered() -> None:
    app = create_app()
    included_routers = [
        route for route in app.routes if type(route).__name__ == "_IncludedRouter"
    ]

    assert len(included_routers) >= 2
