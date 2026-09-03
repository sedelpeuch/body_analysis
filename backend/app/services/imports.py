"""Orchestration de l'import ZIP Samsung Health.

Réutilise discover_source et run_ingestion du pipeline existant sans les
réécrire. Ce module gère ce qu'ils ne gèrent pas : la validation du fichier
reçu, l'extraction sûre dans un répertoire jetable, et la création précoce
du IngestionRun pour qu'un identifiant soit disponible dès la réponse HTTP,
avant que l'ingestion elle-même — potentiellement longue — ne démarre en
tâche de fond.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import ValidationError
from app.ingestion.samsung.pipeline import discover_source, run_ingestion
from app.ingestion.zip_safety import safe_extract
from app.models import IngestionRun, IngestionStatus

IMPORT_KIND = "samsung_zip"

_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


async def create_pending_run(
    session: AsyncSession, *, source_name: str
) -> IngestionRun:
    """Crée la ligne de suivi avant même l'extraction de l'archive.

    C'est ce qui permet au front d'obtenir un identifiant à interroger dès
    la réponse de POST /api/imports/samsung-zip.
    """
    run = IngestionRun(
        kind=IMPORT_KIND, source_name=source_name, status=IngestionStatus.RUNNING
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


def validate_zip_signature(header: bytes) -> None:
    """Vérifie que le fichier reçu commence par une signature ZIP connue,
    quel que soit le Content-Type ou le nom de fichier déclarés."""
    if not header.startswith(_ZIP_SIGNATURES):
        raise ValidationError("Le fichier envoyé n'est pas une archive ZIP valide.")


async def run_zip_import(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    run_id: int,
    zip_path: Path,
) -> None:
    """Tâche de fond : extrait l'archive puis délègue à run_ingestion.

    Exécutée avec sa propre session, indépendante de celle de la requête
    HTTP déjà répondue. Le répertoire d'extraction et le fichier ZIP
    temporaire sont nettoyés dans un finally, y compris en cas d'échec.
    """
    extract_dir = Path(tempfile.mkdtemp(prefix="ba-import-"))
    try:
        safe_extract(zip_path, extract_dir)
        source = discover_source(extract_dir)

        async with session_factory() as session:
            run = await session.get(IngestionRun, run_id)
            await run_ingestion(
                session,
                source,
                kind=IMPORT_KIND,
                source_name=run.source_name,
                run=run,
            )
    except Exception as error:
        async with session_factory() as session:
            run = await session.get(IngestionRun, run_id)
            if run is not None and run.status is not IngestionStatus.FAILED:
                run.status = IngestionStatus.FAILED
                run.error = f"{type(error).__name__}: {error}"
                await session.commit()
        raise
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
