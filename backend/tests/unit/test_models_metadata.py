"""Vérifie la forme du schéma sans avoir besoin d'une base de données."""

from app.models import Base

EXPECTED_TABLES = {
    "body_measurement",
    "nutrition_entry",
    "phase",
    "workout",
    "workout_sample",
    "workout_location",
    "swim_length",
    "strength_set",
    "workout_extra",
    "photo",
    "ingestion_run",
}


def test_all_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_fact_tables_have_unique_source_uuid() -> None:
    """L'idempotence du ré-import repose entièrement sur cette contrainte."""
    for name in ("body_measurement", "nutrition_entry", "workout"):
        column = Base.metadata.tables[name].c["source_uuid"]
        assert column.unique is True
        assert column.nullable is False


def test_timestamps_are_timezone_aware() -> None:
    """Un TIMESTAMP sans fuseau ferait dériver les agrégations par jour."""
    checks = [
        ("body_measurement", "measured_at"),
        ("nutrition_entry", "consumed_at"),
        ("workout", "started_at"),
        ("workout_sample", "at"),
        ("workout_location", "at"),
    ]
    for table, column in checks:
        assert Base.metadata.tables[table].c[column].type.timezone is True


def test_child_tables_cascade_from_workout() -> None:
    """Réingérer une séance doit pouvoir remplacer ses séries filles."""
    for name in (
        "workout_sample",
        "workout_location",
        "swim_length",
        "strength_set",
        "workout_extra",
    ):
        fk = next(iter(Base.metadata.tables[name].c["workout_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"


def test_photo_is_unique_per_date_and_tag() -> None:
    constraints = {
        tuple(sorted(c.name for c in uc.columns))
        for uc in Base.metadata.tables["photo"].constraints
        if hasattr(uc, "columns") and len(uc.columns) == 2
    }
    assert ("tag", "taken_on") in constraints
