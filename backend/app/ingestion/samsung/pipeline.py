"""Orchestration d'une ingestion complète et journalisation du run."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.phases import read_phases
from app.ingestion.refresh import refresh_materialized_views
from app.ingestion.samsung.activity import map_daily_activity, map_step_daily_trend
from app.ingestion.samsung.assembler import build_workout_bundle
from app.ingestion.samsung.energy import map_energy_expenditure
from app.ingestion.samsung.loader import (
    upsert_body_measurements,
    upsert_daily_activities,
    upsert_energy_expenditures,
    upsert_heart_rate_readings,
    upsert_hrv_readings,
    upsert_nutrition_details,
    upsert_nutrition_entries,
    upsert_oxygen_saturation_readings,
    upsert_phases,
    upsert_respiratory_rate_readings,
    upsert_skin_temperature_readings,
    upsert_sleep_sessions,
    upsert_sleep_stages,
    upsert_step_daily_trends,
    upsert_stress_readings,
    upsert_workout_bundle,
)
from app.ingestion.samsung.mapper import (
    map_body_measurement,
    map_nutrition_entry,
    map_workout,
)
from app.ingestion.samsung.nutrition_detail import map_nutrition_detail
from app.ingestion.samsung.parsers import read_samsung_csv
from app.ingestion.samsung.sleep import map_sleep_session, map_sleep_stage
from app.ingestion.samsung.vitals import (
    map_heart_rate_reading,
    map_hrv_reading,
    map_oxygen_saturation_reading,
    map_respiratory_rate_reading,
    map_skin_temperature_reading,
    map_stress_reading,
)
from app.models import IngestionRun, IngestionStatus, Workout

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
    nutrition_csv: Path | None = None
    calories_burned_csv: Path | None = None
    sleep_csv: Path | None = None
    sleep_stage_csv: Path | None = None
    hrv_csv: Path | None = None
    hrv_dir: Path | None = None
    heart_rate_csv: Path | None = None
    stress_csv: Path | None = None
    day_summary_csv: Path | None = None
    step_daily_trend_csv: Path | None = None
    oxygen_saturation_csv: Path | None = None
    respiratory_rate_csv: Path | None = None
    skin_temperature_csv: Path | None = None
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


def _latest_json_dir(root: Path, prefix: str) -> Path | None:
    candidates = sorted(
        path
        for path in root.glob(f"{prefix}*")
        if path.is_dir() and path.name.startswith(prefix)
    )
    if not candidates:
        jsons_root = root / "jsons"
        if jsons_root.is_dir():
            candidates = sorted(
                path
                for path in jsons_root.glob(f"{prefix}*")
                if path.is_dir() and path.name.startswith(prefix)
            )
    return candidates[-1] if candidates else None


def discover_source(root: Path) -> SamsungSource:
    exercise_candidates = sorted(
        path
        for path in root.glob("com.samsung.shealth.exercise.*.csv")
        if path.is_file() and _EXERCISE_CSV_RE.match(path.name)
    )
    phases_json = root / "phases.json"
    hrv_dir = _latest_json_dir(root, "com.samsung.health.hrv")
    return SamsungSource(
        weight_csv=_latest(root, "com.samsung.health.weight.*.csv"),
        food_csv=_latest(root, "com.samsung.health.food_intake.*.csv"),
        nutrition_csv=_latest(root, "com.samsung.health.nutrition.*.csv"),
        calories_burned_csv=_latest(
            root,
            "com.samsung.shealth.calories_burned.details.*.csv",
        ),
        sleep_csv=_latest(root, "com.samsung.shealth.sleep.*.csv"),
        sleep_stage_csv=_latest(root, "com.samsung.health.sleep_stage.*.csv"),
        hrv_csv=_latest(root, "com.samsung.health.hrv.*.csv"),
        hrv_dir=hrv_dir,
        heart_rate_csv=_latest(root, "com.samsung.shealth.tracker.heart_rate.*.csv"),
        stress_csv=_latest(root, "com.samsung.shealth.stress.*.csv"),
        day_summary_csv=_latest(
            root,
            "com.samsung.shealth.activity.day_summary.*.csv",
        ),
        step_daily_trend_csv=_latest(
            root,
            "com.samsung.shealth.step_daily_trend.*.csv",
        ),
        oxygen_saturation_csv=_latest(
            root,
            "com.samsung.shealth.tracker.oxygen_saturation.*.csv",
        ),
        respiratory_rate_csv=_latest(
            root,
            "com.samsung.health.respiratory_rate.*.csv",
        ),
        skin_temperature_csv=_latest(
            root,
            "com.samsung.health.skin_temperature.*.csv",
        ),
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
    run: IngestionRun | None = None,
) -> IngestionRun:
    """Ingère un export et journalise le résultat.

    En cas d'échec le run est marqué FAILED avec son message avant que
    l'exception soit relancée : l'appelant décide quoi en faire, mais la
    trace en base ne se perd jamais.

    run : une ligne IngestionRun déjà créée et committée à réutiliser plutôt
    que d'en créer une nouvelle. Sert l'import HTTP, où l'identifiant du run
    doit être connu avant que l'ingestion, potentiellement longue, ne
    démarre en tâche de fond.
    """
    if run is None:
        run = IngestionRun(
            kind=kind,
            source_name=source_name,
            status=IngestionStatus.RUNNING,
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
                session,
                records,
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
                session,
                entries,
            )

        if source.nutrition_csv is not None:
            details = [
                detail
                for detail in (
                    map_nutrition_detail(row)
                    for row in read_samsung_csv(source.nutrition_csv)
                )
                if detail is not None
            ]
            counts["nutrition_details"] = await upsert_nutrition_details(
                session,
                details,
            )

        if source.calories_burned_csv is not None:
            expenditures = [
                expenditure
                for expenditure in (
                    map_energy_expenditure(row)
                    for row in read_samsung_csv(source.calories_burned_csv)
                )
                if expenditure is not None
            ]
            counts["energy_expenditures"] = await upsert_energy_expenditures(
                session,
                expenditures,
            )

        if source.sleep_csv is not None:
            sessions = [
                session_record
                for session_record in (
                    map_sleep_session(row) for row in read_samsung_csv(source.sleep_csv)
                )
                if session_record is not None
            ]
            counts["sleep_sessions"] = await upsert_sleep_sessions(
                session,
                sessions,
            )

        if source.sleep_stage_csv is not None:
            stages = [
                stage
                for stage in (
                    map_sleep_stage(row)
                    for row in read_samsung_csv(source.sleep_stage_csv)
                )
                if stage is not None
            ]
            counts["sleep_stages"] = await upsert_sleep_stages(session, stages)

        if source.hrv_csv is not None:
            hrv_rows = []
            hrv_base = source.hrv_dir or Path()
            for row in read_samsung_csv(source.hrv_csv):
                record = map_hrv_reading(row, hrv_base)
                if record is not None:
                    hrv_rows.append(record)
            counts["hrv_readings"] = await upsert_hrv_readings(session, hrv_rows)

        if source.heart_rate_csv is not None:
            heart_rates = [
                record
                for record in (
                    map_heart_rate_reading(row)
                    for row in read_samsung_csv(source.heart_rate_csv)
                )
                if record is not None
            ]
            counts["heart_rate_readings"] = await upsert_heart_rate_readings(
                session,
                heart_rates,
            )

        if source.stress_csv is not None:
            stress = [
                record
                for record in (
                    map_stress_reading(row)
                    for row in read_samsung_csv(source.stress_csv)
                )
                if record is not None
            ]
            counts["stress_readings"] = await upsert_stress_readings(session, stress)

        if source.oxygen_saturation_csv is not None:
            o2 = [
                record
                for record in (
                    map_oxygen_saturation_reading(row)
                    for row in read_samsung_csv(source.oxygen_saturation_csv)
                )
                if record is not None
            ]
            counts[
                "oxygen_saturation_readings"
            ] = await upsert_oxygen_saturation_readings(
                session,
                o2,
            )

        if source.respiratory_rate_csv is not None:
            rr = [
                record
                for record in (
                    map_respiratory_rate_reading(row)
                    for row in read_samsung_csv(source.respiratory_rate_csv)
                )
                if record is not None
            ]
            counts[
                "respiratory_rate_readings"
            ] = await upsert_respiratory_rate_readings(
                session,
                rr,
            )

        if source.skin_temperature_csv is not None:
            skin = [
                record
                for record in (
                    map_skin_temperature_reading(row)
                    for row in read_samsung_csv(source.skin_temperature_csv)
                )
                if record is not None
            ]
            counts[
                "skin_temperature_readings"
            ] = await upsert_skin_temperature_readings(
                session,
                skin,
            )

        if source.day_summary_csv is not None:
            daily_activity = [
                record
                for record in (
                    map_daily_activity(row)
                    for row in read_samsung_csv(source.day_summary_csv)
                )
                if record is not None
            ]
            counts["daily_activities"] = await upsert_daily_activities(
                session,
                daily_activity,
            )

        if source.step_daily_trend_csv is not None:
            step_trends = [
                record
                for record in (
                    map_step_daily_trend(row)
                    for row in read_samsung_csv(source.step_daily_trend_csv)
                )
                if record is not None
            ]
            counts["step_daily_trends"] = await upsert_step_daily_trends(
                session,
                step_trends,
            )

        if source.exercise_csv is not None and source.exercise_dir is not None:
            counts.update(
                await _ingest_workouts(
                    session,
                    source.exercise_csv,
                    source.exercise_dir,
                ),
            )

        if source.phases_json is not None:
            counts["phases"] = await upsert_phases(
                session,
                read_phases(source.phases_json),
            )

        await refresh_materialized_views(session, concurrently=False)
        run.status = IngestionStatus.SUCCESS
    except Exception as error:
        await session.rollback()
        run.status = IngestionStatus.FAILED
        run.error = f"{type(error).__name__}: {error}"
        raise
    finally:
        run.counts = counts
        run.finished_at = datetime.now(UTC)
        session.add(run)
        await session.commit()

    return run


async def _existing_workout_versions(
    session: AsyncSession,
) -> dict[str, datetime | None]:
    """Charge en une requête {source_uuid: source_updated_at} des séances
    déjà en base, pour sauter le retraitement (JSON + échantillons) des
    séances inchangées lors d'un ré-import complet."""
    rows = await session.execute(select(Workout.source_uuid, Workout.source_updated_at))
    return dict(rows.all())


async def _ingest_workouts(
    session: AsyncSession,
    exercise_csv: Path,
    exercise_dir: Path,
) -> dict[str, int]:
    """Traite les séances une par une pour ne jamais tenir les 2,8 M
    d'échantillons en mémoire simultanément.

    Un ré-import complet (ZIP réexporté en entier depuis le téléphone) revoit
    chaque séance à chaque fois. La comparaison à existing_versions évite de
    relire les JSON et de reconstruire les échantillons d'une séance dont
    l'update_time source n'a pas bougé depuis le dernier import."""
    counts = {
        "workouts": 0,
        "workouts_skipped": 0,
        "samples": 0,
        "locations": 0,
        "swim_lengths": 0,
        "strength_sets": 0,
    }
    existing_versions = await _existing_workout_versions(session)
    for row in read_samsung_csv(exercise_csv):
        light = map_workout(row)
        if light is None:
            continue
        if (
            light.source_uuid in existing_versions
            and existing_versions[light.source_uuid] == light.source_updated_at
        ):
            counts["workouts_skipped"] += 1
            continue

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
