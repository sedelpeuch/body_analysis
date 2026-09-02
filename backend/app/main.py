"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
