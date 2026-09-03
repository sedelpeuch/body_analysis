"""Endpoints d'import : réception du ZIP, suivi de la progression.

L'upload est reçu en flux et écrit sur disque par blocs : une archive réelle
atteint 1,3 Go, jamais chargée entièrement en mémoire. Seule la validation
de la signature ZIP et la création de la ligne de suivi se font avant la
réponse ; l'extraction et l'ingestion tournent en tâche de fond, le front
interrogeant GET /api/imports/{id} pour suivre la progression.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import get_session, get_session_factory
from app.errors import NotFoundError
from app.models import IngestionRun
from app.schemas.imports import IngestionRunOut
from app.services.imports import (
    create_pending_run,
    run_zip_import,
    validate_zip_signature,
)

router = APIRouter(prefix="/imports", tags=["imports"])

UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 Mo : jamais l'archive entière en mémoire


async def _run_zip_import_in_background(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    run_id: int,
    zip_path: Path,
) -> None:
    """Enveloppe run_zip_import pour BackgroundTasks.

    run_zip_import relance l'exception après avoir marqué le run FAILED,
    pour que ses propres appelants directs puissent la voir. Ici, la
    réponse HTTP est déjà partie : laisser l'exception remonter ferait
    planter Starlette en tentant de construire une réponse d'erreur sur une
    réponse déjà envoyée. Le run FAILED en base est la seule trace requise.
    """
    try:
        await run_zip_import(session_factory, run_id=run_id, zip_path=zip_path)
    except Exception:
        pass


@router.post("/samsung-zip", response_model=IngestionRunOut, status_code=202)
async def import_samsung_zip(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    session: AsyncSession = Depends(get_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(
        get_session_factory,
    ),
) -> IngestionRunOut:
    first_chunk = await file.read(UPLOAD_CHUNK_SIZE)
    validate_zip_signature(first_chunk)

    fd, tmp_name = tempfile.mkstemp(prefix="ba-upload-", suffix=".zip")
    tmp_path = Path(tmp_name)
    with open(fd, "wb") as handle:
        handle.write(first_chunk)
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            handle.write(chunk)

    run = await create_pending_run(session, source_name=file.filename or "export.zip")

    background_tasks.add_task(
        _run_zip_import_in_background, session_factory, run_id=run.id, zip_path=tmp_path
    )
    return IngestionRunOut.model_validate(run)


@router.get("", response_model=list[IngestionRunOut])
async def list_imports(
    session: AsyncSession = Depends(get_session),
) -> list[IngestionRunOut]:
    query = select(IngestionRun).order_by(IngestionRun.started_at.desc())
    runs = (await session.execute(query)).scalars().all()
    return [IngestionRunOut.model_validate(run) for run in runs]


@router.get("/{run_id}", response_model=IngestionRunOut)
async def get_import(
    run_id: int, session: AsyncSession = Depends(get_session)
) -> IngestionRunOut:
    run = await session.get(IngestionRun, run_id)
    if run is None:
        raise NotFoundError(f"Import {run_id} introuvable")
    return IngestionRunOut.model_validate(run)
