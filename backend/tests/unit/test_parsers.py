"""Tests des conversions bas niveau de l'export Samsung."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.ingestion.samsung.parsers import (
    parse_aware_datetime,
    parse_epoch_millis,
    parse_float,
    parse_int,
    parse_json_int,
    parse_utc_offset,
    read_samsung_csv,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "samsung"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("65.6", 65.6),
        ("1.4374734", 1.4374734),
        ("-0.002120687859132886", -0.002120687859132886),
        ("", None),
        ("   ", None),
        (None, None),
        ("abc", None),
    ],
)
def test_parse_float(raw: object, expected: float | None) -> None:
    assert parse_float(raw) == expected


def test_parse_float_never_returns_nan() -> None:
    """Une valeur absente doit être None, jamais NaN : le code Streamlit
    remplaçait les vides par math.nan, ce qui contaminait les moyennes."""
    assert parse_float("") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("100002", 100002), ("0", 0), ("-1", -1), ("", None), (None, None)],
)
def test_parse_int(raw: object, expected: int | None) -> None:
    assert parse_int(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (100.0, 100),
        (99, 99),
        (0.0, 0),
        (100.6, 101),
        (None, None),
        ("100", None),  # chaîne CSV : hors périmètre, cf. parse_int
        (True, None),
    ],
)
def test_parse_json_int(raw: object, expected: int | None) -> None:
    """Samsung sérialise certains champs entiers des JSON annexes en float
    (heart_rate: 100.0) et d'autres en int réel, sans cohérence. Un bug
    découvert en exploitant l'export réel : parse_int rejetait "100.0" via
    sa regex stricte, laissant heart_rate/cadence/elapsed_ms NULL sur les
    2,4 M lignes de workout_sample."""
    assert parse_json_int(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("UTC+0200", timezone(timedelta(hours=2))),
        ("UTC+0100", timezone(timedelta(hours=1))),
        ("UTC-0500", timezone(timedelta(hours=-5))),
        ("UTC+0530", timezone(timedelta(hours=5, minutes=30))),
        ("", None),
        (None, None),
        ("Europe/Paris", None),
    ],
)
def test_parse_utc_offset(raw: object, expected: timezone | None) -> None:
    assert parse_utc_offset(raw) == expected


def test_parse_aware_datetime_combines_local_time_and_offset() -> None:
    result = parse_aware_datetime("2026-08-31 06:29:10.346", "UTC+0200")

    assert result == datetime(
        2026, 8, 31, 6, 29, 10, tzinfo=timezone(timedelta(hours=2))
    )


def test_parse_aware_datetime_without_offset_assumes_utc() -> None:
    """Sans décalage connu on ne peut pas inventer un fuseau ; on retient
    UTC pour rester déterministe et comparable."""
    result = parse_aware_datetime("2026-08-31 06:29:10.346", "")

    assert result == datetime(2026, 8, 31, 6, 29, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    "raw", ["", None, "pas une date", "2026-02-30 10:00:00", "2026-13-01 10:00:00"]
)
def test_parse_aware_datetime_rejects_invalid(raw: object) -> None:
    assert parse_aware_datetime(raw, "UTC+0200") is None


def test_parse_epoch_millis() -> None:
    result = parse_epoch_millis(1644085620000)

    assert result == datetime(2022, 2, 5, 18, 27, tzinfo=UTC)


@pytest.mark.parametrize("raw", ["", None, "abc"])
def test_parse_epoch_millis_rejects_invalid(raw: object) -> None:
    assert parse_epoch_millis(raw) is None


def test_read_samsung_csv_skips_metadata_line() -> None:
    rows = list(read_samsung_csv(FIXTURES / "weight_sample.csv"))

    assert len(rows) == 2
    assert rows[0]["weight"] == "90.0"
    assert rows[1]["datauuid"] == "f631923e-bc08-404a-8d0c-9468aa4dee2b"


def test_read_samsung_csv_strips_bom_from_first_header() -> None:
    """Les exports sont en utf-8-sig ; sans traitement, la première colonne
    s'appellerait '﻿start_time' et serait introuvable."""
    rows = list(read_samsung_csv(FIXTURES / "weight_sample.csv"))

    assert "start_time" in rows[0]
