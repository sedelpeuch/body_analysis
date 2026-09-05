"""Vérifie la forme des tables de la couche ingestion étendue."""

from app.models import Base

NEW_TABLES = {
    "nutrition_detail",
    "energy_expenditure",
    "sleep_session",
    "sleep_stage",
    "hrv_reading",
    "heart_rate_reading",
    "stress_reading",
    "respiratory_rate_reading",
    "skin_temperature_reading",
    "oxygen_saturation_reading",
    "daily_activity",
    "step_daily_trend",
}


def test_new_tables_are_registered() -> None:
    assert NEW_TABLES.issubset(set(Base.metadata.tables))


def test_all_new_fact_tables_have_unique_source_uuid() -> None:
    for name in NEW_TABLES:
        column = Base.metadata.tables[name].c["source_uuid"]
        assert column.unique is True
        assert column.nullable is False


def test_instant_columns_are_timezone_aware() -> None:
    checks = [
        ("nutrition_detail", "consumed_at"),
        ("sleep_session", "started_at"),
        ("sleep_stage", "started_at"),
        ("hrv_reading", "started_at"),
        ("heart_rate_reading", "started_at"),
        ("stress_reading", "started_at"),
        ("respiratory_rate_reading", "started_at"),
        ("skin_temperature_reading", "started_at"),
        ("oxygen_saturation_reading", "started_at"),
    ]
    for table, column in checks:
        assert Base.metadata.tables[table].c[column].type.timezone is True


def test_day_columns_are_plain_dates() -> None:
    """day_time n'a pas de time_offset dans ces trois exports : seule la
    date est fiable, un TIMESTAMPTZ inventerait un fuseau."""
    for table in ("energy_expenditure", "daily_activity", "step_daily_trend"):
        column = Base.metadata.tables[table].c["day"]
        assert column.type.__class__.__name__ == "Date"


def test_sleep_stage_has_no_hard_foreign_key() -> None:
    """7 segments réels référencent une nuit absente de sleep_session."""
    column = Base.metadata.tables["sleep_stage"].c["sleep_source_uuid"]
    assert not column.foreign_keys
