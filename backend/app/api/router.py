"""Assemble les routers applicatifs sous le préfixe /api."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.analytics import body_router as analytics_body_router
from app.api.analytics import router as analytics_router
from app.api.body import router as body_router
from app.api.imports import router as imports_router
from app.api.nutrition import router as nutrition_router
from app.api.phases import router as phases_router
from app.api.workouts import router as workouts_router
from app.api.workouts import sports_router

api_router = APIRouter(prefix="/api")
api_router.include_router(body_router)
api_router.include_router(analytics_body_router)
api_router.include_router(nutrition_router)
api_router.include_router(phases_router)
api_router.include_router(imports_router)
api_router.include_router(sports_router)
api_router.include_router(workouts_router)
api_router.include_router(analytics_router)
