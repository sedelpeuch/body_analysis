"""Orchestration d'une ingestion complète et journalisation du run."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.phases import read_phases
from app.ingestion.refresh import refresh_materialized_views
from app.ingestion.samsung.assembler import build_workout_bundle
from app.ingestion.samsung.loader import (
    upsert_body_measurements,
    upsert_nutrition_entries,
    upsert_phases,
    upsert_workout_bundle,
)
from app.ingestion.samsung.mapper import map_body_measurement, map_nutrition_entry
from app.ingestion.samsung.parsers import read_samsung_csv
from app.models import IngestionRun, IngestionStatus

EXERCISE_DIR_NAME = "com.samsung.shealth.exercise"

# L'export réel place les JSON par enregistrement sous jsons/ ; le dossier de
# travail historique les a remontés à la racine. Les deux dispositions sont
# acceptées, dans cet ordre de priorité.
EXERCISE_DIR_CANDIDATES = (("jsons", EXERCISE_DIR_NAME), (EXERCISE_DIR_NAME,))
_EXERCISE_CSV_RE = re.compile(r"\Acom\.samsung\.shealth\.exercise\.\d{14}\.csv\Z")

# Commiter tous les 100 paquets : 4 734 séances et leurs 2,8 M
# d'échantillons dans une seule transaction feraient exploser la mémoire.
COMMIT_EVERY = 100


@dataclass(frozen=True, slots=True)
class SamsungSource:
    weight_csv: Path | None = None
    food_csv: Path | None = None
    exercise_csv: Path | None = None
    exercise_dir: Path | None = None
    phases_json: Path | None = None


def _latest(root: Path, pattern: str) -> Path | None:
    """Le nom porte un horodatage à 14 chiffres, l'ordre lexicographique
    est donc l'ordre chronologique."""
    matches = sorted(path for path in root.glob(pattern) if path.is_file())
    return matches[-1] if matches else None


def _exercise_dir(root: Path) -> Path | None:
    for parts in EXERCISE_DIR_CANDIDATES:
        candidate = root.joinpath(*parts)
        if candidate.is_dir():
            return candidate
    return None


def discover_source(root: Path) -> SamsungSource:
    exercise_candidates = sorted(
        path
        for path in root.glob("com.samsung.shealth.exercise.*.csv")
        if path.is_file() and _EXERCISE_CSV_RE.match(path.name)
    )
    phases_json = root / "phases.json"
    return SamsungSource(
        weight_csv=_latest(root, "com.samsung.health.weight.*.csv"),
        food_csv=_latest(root, "com.samsung.health.food_intake.*.csv"),
        exercise_csv=exercise_candidates[-1] if exercise_candidates else None,
        exercise_dir=_exercise_dir(root),
        phases_json=phases_json if phases_json.is_file() else None,
    )


async def run_ingestion(
    session: AsyncSession,
    source: SamsungSource,
    *,
    kind: str,
    source_name: str,
) -> IngestionRun:
    """Ingère un export et journalise le résultat.

    En cas d'échec le run est marqué FAILED avec son message avant que
    l'exception soit relancée : l'appelant décide quoi en faire, mais la
    trace en base ne se perd jamais.
    """
    run = IngestionRun(
        kind=kind, source_name=source_name, status=IngestionStatus.RUNNING
    )
    session.add(run)
    await session.commit()

    counts: dict[str, int] = {}
    try:
        if source.weight_csv is not None:
            records = [
                record
                for record in (
                    map_body_measurement(row)
                    for row in read_samsung_csv(source.weight_csv)
                )
                if record is not None
            ]
            counts["body_measurements"] = await upsert_body_measurements(
                session, records
            )

        if source.food_csv is not None:
            entries = [
                entry
                for entry in (
                    map_nutrition_entry(row)
                    for row in read_samsung_csv(source.food_csv)
                )
                if entry is not None
            ]
            counts["nutrition_entries"] = await upsert_nutrition_entries(
                session, entries
            )

        if source.exercise_csv is not None and source.exercise_dir is not None:
            counts.update(
                await _ingest_workouts(
                    session, source.exercise_csv, source.exercise_dir
                )
            )

        if source.phases_json is not None:
            counts["phases"] = await upsert_phases(
                session, read_phases(source.phases_json)
            )

        await refresh_materialized_views(session, concurrently=False)
        run.status = IngestionStatus.SUCCESS
    except Exception as error:
        await session.rollback()
        run = await session.get(IngestionRun, run.id)
        run.status = IngestionStatus.FAILED
        run.error = f"{type(error).__name__}: {error}"
        raise
    finally:
        run.counts = counts
        run.finished_at = datetime.now(UTC)
        session.add(run)
        await session.commit()

    return run


async def _ingest_workouts(
    session: AsyncSession, exercise_csv: Path, exercise_dir: Path
) -> dict[str, int]:
    """Traite les séances une par une pour ne jamais tenir les 2,8 M
    d'échantillons en mémoire simultanément."""
    counts = {
        "workouts": 0,
        "samples": 0,
        "locations": 0,
        "swim_lengths": 0,
        "strength_sets": 0,
    }
    for row in read_samsung_csv(exercise_csv):
        bundle = build_workout_bundle(row, exercise_dir)
        if bundle is None:
            continue
        await upsert_workout_bundle(session, bundle)
        counts["workouts"] += 1
        counts["samples"] += len(bundle.samples)
        counts["locations"] += len(bundle.locations)
        counts["swim_lengths"] += len(bundle.swim_lengths)
        counts["strength_sets"] += len(bundle.strength_sets)
        if counts["workouts"] % COMMIT_EVERY == 0:
            await session.commit()
    await session.commit()
    return counts
