"""Tests de la lecture de phases.json."""

from datetime import date
from pathlib import Path

from app.ingestion.phases import read_phases

FIXTURE = Path(__file__).parent.parent / "fixtures" / "phases.json"


def test_reads_phase_without_objectives() -> None:
    phases = read_phases(FIXTURE)

    free = next(p for p in phases if p.name == "Phase libre")
    assert free.kind == "free"
    assert free.starts_on == date(2023, 1, 1)
    assert free.ends_on == date(2023, 12, 31)
    assert free.weight_target_kg is None
    assert free.daily_calories_target is None


def test_maps_objectives_including_renamed_muscle_target() -> None:
    phases = read_phases(FIXTURE)

    cut = next(p for p in phases if p.name == "Première sèche")
    assert cut.weight_target_kg == 70.0
    assert cut.body_fat_target_pct == 20.0
    assert cut.skeletal_muscle_target_kg == 30.0
    assert cut.daily_calories_target == 1900


def test_skips_entries_with_unreadable_dates() -> None:
    assert all(p.name != "Cassée" for p in read_phases(FIXTURE))


def test_unknown_kind_falls_back_to_free() -> None:
    phases = read_phases(FIXTURE)

    assert next(p for p in phases if p.name == "Type inconnu").kind == "free"


def test_result_is_sorted_by_start_date() -> None:
    phases = read_phases(FIXTURE)

    assert [p.starts_on for p in phases] == sorted(p.starts_on for p in phases)


def test_missing_file_yields_empty_list(tmp_path: Path) -> None:
    assert read_phases(tmp_path / "absent.json") == []
