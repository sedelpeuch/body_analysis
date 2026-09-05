"""Fabrique de l'application FastAPI."""

from fastapi import FastAPI

from app.api.photos import router as photos_router
from app.api.router import api_router
from app.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Body Analysis API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(api_router)
    app.include_router(photos_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
