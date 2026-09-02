"""Routes de lecture de la famille nutrition."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DateRangeDep, DbSession
from app.schemas.common import Page
from app.schemas.nutrition import DailyNutritionOut, EntryOut, NutritionBreakdownOut
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
