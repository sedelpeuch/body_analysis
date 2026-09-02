"""Endpoints CRUD des phases."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.phases import PhaseCreate, PhaseOut, PhaseUpdate
from app.services import phases as phases_service

router = APIRouter(prefix="/api/phases", tags=["phases"])


@router.get("", response_model=list[PhaseOut])
async def list_phases(session: AsyncSession = Depends(get_session)) -> list[PhaseOut]:
    phases = await phases_service.list_phases(session)
    return [PhaseOut.model_validate(p) for p in phases]


@router.post("", response_model=PhaseOut, status_code=201)
async def create_phase(
    payload: PhaseCreate, session: AsyncSession = Depends(get_session)
) -> PhaseOut:
    phase = await phases_service.create_phase(session, payload)
    return PhaseOut.model_validate(phase)


@router.get("/{phase_id}", response_model=PhaseOut)
async def get_phase(phase_id: int, session: AsyncSession = Depends(get_session)) -> PhaseOut:
    phase = await phases_service.get_phase(session, phase_id)
    return PhaseOut.model_validate(phase)


@router.patch("/{phase_id}", response_model=PhaseOut)
async def update_phase(
    phase_id: int, payload: PhaseUpdate, session: AsyncSession = Depends(get_session)
) -> PhaseOut:
    phase = await phases_service.update_phase(session, phase_id, payload)
    return PhaseOut.model_validate(phase)


@router.delete("/{phase_id}", status_code=204)
async def delete_phase(
    phase_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    await phases_service.delete_phase(session, phase_id)
    return Response(status_code=204)
