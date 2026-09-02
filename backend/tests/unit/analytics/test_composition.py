"""Tests de la recomposition corporelle — spec 5.2.

La grandeur qui compte pendant une sèche n'est pas le pourcentage de masse
grasse (ambigu, il bouge aussi quand la masse maigre bouge) mais les deltas
en kilos des deux masses.
"""

from datetime import date

from app.analytics.composition import CompositionPoint, compute_recomposition

POINTS = [
    CompositionPoint(at=date(2026, 1, 1), fat_mass_kg=18.0, lean_mass_kg=62.0),
    CompositionPoint(at=date(2026, 1, 15), fat_mass_kg=None, lean_mass_kg=None),
    CompositionPoint(at=date(2026, 2, 1), fat_mass_kg=15.5, lean_mass_kg=61.2),
]


def test_recomposition_reports_fat_and_lean_deltas_in_kg() -> None:
    result = compute_recomposition(POINTS, start=date(2026, 1, 1), end=date(2026, 2, 1))

    assert result.fat_mass_delta_kg == -2.5
    assert result.lean_mass_delta_kg == -0.8


def test_recomposition_is_none_without_data_at_either_end() -> None:
    result = compute_recomposition(POINTS, start=date(2025, 1, 1), end=date(2025, 2, 1))

    assert result.fat_mass_delta_kg is None
    assert result.lean_mass_delta_kg is None


def test_recomposition_never_substitutes_zero_for_missing_side() -> None:
    """Si seule la masse grasse est connue à une date, le delta de masse
    maigre reste None : jamais de zéro inventé."""
    points = [
        CompositionPoint(at=date(2026, 1, 1), fat_mass_kg=18.0, lean_mass_kg=None),
        CompositionPoint(at=date(2026, 2, 1), fat_mass_kg=15.5, lean_mass_kg=61.2),
    ]

    result = compute_recomposition(points, start=date(2026, 1, 1), end=date(2026, 2, 1))

    assert result.fat_mass_delta_kg == -2.5
    assert result.lean_mass_delta_kg is None
