"""Tests de la localisation des fichiers dans un export."""

from pathlib import Path

from app.ingestion.samsung.pipeline import discover_source


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_finds_every_component(tmp_path: Path) -> None:
    _touch(tmp_path / "com.samsung.health.weight.20260831162666.csv")
    _touch(tmp_path / "com.samsung.health.food_intake.20260831162666.csv")
    _touch(tmp_path / "com.samsung.shealth.exercise.20260831162666.csv")
    _touch(tmp_path / "com.samsung.shealth.exercise" / "1" / "a.json")
    _touch(tmp_path / "phases.json")

    source = discover_source(tmp_path)

    assert source.weight_csv is not None
    assert source.food_csv is not None
    assert source.exercise_csv is not None
    assert source.exercise_dir == tmp_path / "com.samsung.shealth.exercise"
    assert source.phases_json is not None


def test_finds_exercise_dir_under_jsons(tmp_path: Path) -> None:
    """Disposition de l'export réel : 87 CSV à la racine, JSON sous jsons/."""
    _touch(tmp_path / "jsons" / "com.samsung.shealth.exercise" / "1" / "a.json")

    source = discover_source(tmp_path)

    assert source.exercise_dir == tmp_path / "jsons" / "com.samsung.shealth.exercise"


def test_finds_exercise_dir_at_root(tmp_path: Path) -> None:
    """Disposition du dossier de travail historique, remonté à la racine."""
    _touch(tmp_path / "com.samsung.shealth.exercise" / "1" / "a.json")

    source = discover_source(tmp_path)

    assert source.exercise_dir == tmp_path / "com.samsung.shealth.exercise"


def test_prefers_jsons_layout_when_both_exist(tmp_path: Path) -> None:
    _touch(tmp_path / "jsons" / "com.samsung.shealth.exercise" / "1" / "a.json")
    _touch(tmp_path / "com.samsung.shealth.exercise" / "1" / "a.json")

    source = discover_source(tmp_path)

    assert source.exercise_dir == tmp_path / "jsons" / "com.samsung.shealth.exercise"


def test_keeps_the_most_recent_export_of_each_kind(tmp_path: Path) -> None:
    _touch(tmp_path / "com.samsung.health.weight.20250101000000.csv")
    _touch(tmp_path / "com.samsung.health.weight.20260831162666.csv")

    source = discover_source(tmp_path)

    assert source.weight_csv.name.endswith("20260831162666.csv")


def test_ignores_exercise_csv_without_timestamp(tmp_path: Path) -> None:
    """L'export contient d'autres CSV commençant pareil ; seul le format à
    14 chiffres est le fichier de séances."""
    _touch(tmp_path / "com.samsung.shealth.exercise.summary.csv")

    assert discover_source(tmp_path).exercise_csv is None


def test_empty_directory_yields_all_none(tmp_path: Path) -> None:
    source = discover_source(tmp_path)

    assert source.weight_csv is None
    assert source.exercise_dir is None
    assert source.phases_json is None
