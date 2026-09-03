"""Routes de lecture de la famille nutrition."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DateRangeDep, DbSession
from app.schemas.common import Page
from app.schemas.nutrition import (
    DailyNutritionOut,
    EntryOut,
    HourlyBucketOut,
    NutritionBreakdownOut,
    TopFoodOut,
)
from app.services import nutrition as nutrition_service
from app.services.nutrition import NUTRITION_PAGE_SIZE

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/daily", response_model=list[DailyNutritionOut])
async def get_daily(session: DbSession, date_range: DateRangeDep):
    rows = await nutrition_service.get_daily(session, date_range)
    return [DailyNutritionOut.model_validate(r) for r in rows]


@router.get("/entries", response_model=Page[EntryOut])
async def get_entries(
    session: DbSession,
    date_range: DateRangeDep,
    page: int = Query(default=1, ge=1),
):
    entries, total = await nutrition_service.list_entries(session, date_range, page)
    return Page[EntryOut](
        items=[EntryOut.model_validate(e) for e in entries],
        page=page,
        page_size=NUTRITION_PAGE_SIZE,
        total=total,
    )


@router.get("/breakdown", response_model=NutritionBreakdownOut)
async def get_breakdown(session: DbSession, date_range: DateRangeDep):
    breakdown = await nutrition_service.get_breakdown(session, date_range)
    return NutritionBreakdownOut.model_validate(breakdown)


@router.get("/eating-window", response_model=list[HourlyBucketOut])
async def get_eating_window(session: DbSession, date_range: DateRangeDep):
    buckets = await nutrition_service.get_eating_window(session, date_range)
    return [HourlyBucketOut.model_validate(b) for b in buckets]


@router.get("/top-foods", response_model=list[TopFoodOut])
async def get_top_foods(
    session: DbSession,
    date_range: DateRangeDep,
    limit: int = Query(default=10, ge=1, le=100),
):
    foods = await nutrition_service.get_top_foods(session, date_range, limit)
    return [TopFoodOut.model_validate(f) for f in foods]
