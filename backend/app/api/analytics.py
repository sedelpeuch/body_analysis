"""Routes des analyses transverses — spec section 6, "Analyses transverses"."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DateRangeDep, DbSession
from app.schemas.analytics import (
    CompositionPointOut,
    EnergyBalanceDayOut,
    LoadBalanceOut,
    RestingHrPointOut,
    TdeeOut,
)
from app.services import analytics as analytics_service

body_router = APIRouter(prefix="/body", tags=["analyses"])
router = APIRouter(prefix="/analytics", tags=["analyses"])


@body_router.get("/composition", response_model=list[CompositionPointOut])
async def get_composition(session: DbSession, date_range: DateRangeDep):
    points = await analytics_service.get_composition(session, date_range)
    return [CompositionPointOut.model_validate(p) for p in points]


@router.get("/tdee", response_model=TdeeOut)
async def get_tdee(
    session: DbSession,
    date_range: DateRangeDep,
    phase_id: int | None = Query(default=None),
):
    estimate = await analytics_service.get_tdee(
        session, phase_id=phase_id, date_range=date_range
    )
    return TdeeOut.model_validate(estimate)


@router.get("/energy-balance", response_model=list[EnergyBalanceDayOut])
async def get_energy_balance(session: DbSession, date_range: DateRangeDep):
    days = await analytics_service.get_energy_balance(session, date_range)
    return [EnergyBalanceDayOut.model_validate(d) for d in days]


@router.get("/resting-hr", response_model=list[RestingHrPointOut])
async def get_resting_hr(session: DbSession, date_range: DateRangeDep):
    points = await analytics_service.get_resting_hr(session, date_range)
    return [RestingHrPointOut.model_validate(p) for p in points]


@router.get("/training-load", response_model=list[LoadBalanceOut])
async def get_training_load(session: DbSession, date_range: DateRangeDep):
    balances = await analytics_service.get_training_load(session, date_range)
    return [LoadBalanceOut.model_validate(b) for b in balances]
