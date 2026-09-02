"""Assemble tous les routers de lecture sous le préfixe /api."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.body import router as body_router
from app.api.nutrition import router as nutrition_router

api_router = APIRouter(prefix="/api")
api_router.include_router(body_router)
api_router.include_router(nutrition_router)
