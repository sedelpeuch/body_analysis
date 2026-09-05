"""Assemblage d'une séance complète à partir d'une ligne CSV et du disque."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from app.ingestion.samsung import json_files
from app.ingestion.samsung.mapper import (
    map_json_references,
    map_strength_sets,
    map_workout,
)
from app.ingestion.samsung.records import ExtraRecord, WorkoutBundle


def build_workout_bundle(
    row: dict[str, str], exercise_dir: Path
) -> WorkoutBundle | None:
    workout = map_workout(row)
    if workout is None:
        return None

    references = map_json_references(row)

    live = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.live_data)
    )
    location = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.location_data)
    )
    additional = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.additional)
    )
    sensing = json_files.load_json(
        json_files.resolve_json_path(exercise_dir, references.sensing_status)
    )

    thresholds = json_files.map_heart_rate_thresholds(sensing)
    workout = dataclasses.replace(
        workout,
        pool_length_m=json_files.map_pool_length(additional),
        max_hr_custom=thresholds.max_hr_custom,
        max_hr_auto=thresholds.max_hr_auto,
        hr_aerobic_threshold=thresholds.aerobic,
        hr_anaerobic_threshold=thresholds.anaerobic,
        resting_hr=thresholds.resting,
    )

    extras: list[ExtraRecord] = []
    if isinstance(additional, dict):
        extras.append(ExtraRecord(kind="additional", payload=additional))
    if isinstance(sensing, dict):
        extras.append(ExtraRecord(kind="sensing_status", payload=sensing))

    return WorkoutBundle(
        workout=workout,
        samples=json_files.map_samples(live),
        locations=json_files.map_locations(location),
        swim_lengths=json_files.map_swim_lengths(additional),
        strength_sets=map_strength_sets(row, workout.sport),
        extras=extras,
    )
