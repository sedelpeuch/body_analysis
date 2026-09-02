"""Tests des deltas génériques sur série temporelle à trous."""

from datetime import date

from app.analytics.deltas import (
    TimePoint,
    compute_change_between,
    compute_delta,
    find_nearest_at_or_before,
)

POINTS = [
    TimePoint(at=date(2026, 1, 1), value=80.0),
    TimePoint(at=date(2026, 1, 10), value=None),
    TimePoint(at=date(2026, 1, 15), value=78.5),
    TimePoint(at=date(2026, 1, 31), value=77.0),
]


def test_find_nearest_at_or_before_exact_match() -> None:
    result = find_nearest_at_or_before(POINTS, date(2026, 1, 15))

    assert result == TimePoint(at=date(2026, 1, 15), value=78.5)


def test_find_nearest_at_or_before_skips_null_values() -> None:
    """Le point du 10 janvier existe mais sa valeur est None : on ne doit
    jamais le retenir, sous peine de propager un trou comme s'il valait 0."""
    result = find_nearest_at_or_before(POINTS, date(2026, 1, 12))

    assert result == TimePoint(at=date(2026, 1, 1), value=80.0)


def test_find_nearest_at_or_before_returns_none_when_too_early() -> None:
    result = find_nearest_at_or_before(POINTS, date(2025, 12, 31))

    assert result is None


def test_compute_delta_over_window() -> None:
    delta = compute_delta(POINTS, reference=date(2026, 1, 31), window_days=30)

    assert delta.window_days == 30
    assert delta.start_value == 80.0
    assert delta.end_value == 77.0
    assert delta.change == -3.0


def test_compute_delta_is_none_when_window_predates_data() -> None:
    delta = compute_delta(POINTS, reference=date(2026, 1, 5), window_days=90)

    assert delta.start_value is None
    assert delta.end_value == 80.0
    assert delta.change is None


def test_compute_change_between_explicit_dates() -> None:
    delta = compute_change_between(POINTS, start=date(2026, 1, 1), end=date(2026, 1, 15))

    assert delta.window_days == 14
    assert delta.start_value == 80.0
    assert delta.end_value == 78.5
    assert delta.change == -1.5


def test_compute_change_between_empty_series_is_all_none() -> None:
    delta = compute_change_between([], start=date(2026, 1, 1), end=date(2026, 1, 15))

    assert delta.start_value is None
    assert delta.end_value is None
    assert delta.change is None
