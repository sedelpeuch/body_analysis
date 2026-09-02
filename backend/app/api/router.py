"""Assemble tous les routers de lecture sous le préfixe /api."""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api")
