"""Endpoints lecture des phases."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.phases import PhaseOut, PhaseReportOut
from app.services import phases as phases_service

router = APIRouter(prefix="/phases", tags=["phases"])


@router.get("", response_model=list[PhaseOut])
async def list_phases(session: AsyncSession = Depends(get_session)) -> list[PhaseOut]:
    phases = await phases_service.list_phases(session)
    return [PhaseOut.model_validate(p) for p in phases]


@router.get("/current", response_model=PhaseOut | None)
async def get_current_phase(
    session: AsyncSession = Depends(get_session),
    today: date = Query(default_factory=date.today),
) -> PhaseOut | None:
    phase = await phases_service.get_current_phase(session, today)
    return PhaseOut.model_validate(phase) if phase is not None else None


@router.get("/{phase_id}", response_model=PhaseOut)
async def get_phase(
    phase_id: int, session: AsyncSession = Depends(get_session)
) -> PhaseOut:
    phase = await phases_service.get_phase(session, phase_id)
    return PhaseOut.model_validate(phase)


@router.get("/{phase_id}/report", response_model=PhaseReportOut)
async def get_phase_report(
    phase_id: int,
    session: AsyncSession = Depends(get_session),
    today: date = Query(default_factory=date.today),
) -> PhaseReportOut:
    report = await phases_service.get_phase_report(session, phase_id, today=today)
    return PhaseReportOut.model_validate(report)
