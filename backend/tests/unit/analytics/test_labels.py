"""Tests des libellés nutrition — codes relevés en spec section 4.2."""

import pytest

from app.analytics.labels import meal_type_label, unit_label


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (100001, "Petit-déjeuner"),
        (100002, "Déjeuner"),
        (100003, "Dîner"),
        (100004, "Collation"),
        (100005, "Collation matin"),
        (100006, "Collation soir"),
    ],
)
def test_known_meal_types(code: int, expected: str) -> None:
    assert meal_type_label(code) == expected


def test_unknown_meal_type_is_labelled_not_dropped() -> None:
    assert meal_type_label(999999) == "Autre"


def test_missing_meal_type_is_explicit() -> None:
    assert meal_type_label(None) == "Non renseigné"


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (120001, "Grammes"),
        (120002, "Millilitres"),
        (120004, "Portion"),
        (120005, "Unité"),
        (-1, "Non spécifié"),
    ],
)
def test_known_units(code: int, expected: str) -> None:
    assert unit_label(code) == expected


def test_unknown_unit_is_labelled_not_dropped() -> None:
    assert unit_label(424242) == "Autre"


def test_missing_unit_is_explicit() -> None:
    assert unit_label(None) == "Non renseigné"
