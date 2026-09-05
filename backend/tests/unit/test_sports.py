"""Tests de la résolution du sport depuis le code d'exercice Samsung."""

import pytest

from app.ingestion.samsung.sports import resolve_sport


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (1001, "Marche"),
        (1002, "Course à pied"),
        (11007, "Vélo"),
        (13001, "Randonnée"),
        (14001, "Natation"),
        (15004, "Rameur"),
        (10025, "Poids du corps"),
    ],
)
def test_known_codes_win_over_everything(code: int, expected: str) -> None:
    """Le code d'exercice fait foi, avec ou sans séries dans les données."""
    assert resolve_sport(code, has_sets=False) == expected
    assert resolve_sport(code, has_sets=True) == expected


def test_swimming_with_sets_stays_swimming() -> None:
    """Verrou de non-régression du bug corrigé.

    69 séances réelles portent le code 14001 tout en ayant des reps dans
    subset_data. L'ancienne heuristique testait les reps en premier et les
    classait en Musculation, soit 21 % des séances de natation perdues pour
    l'analyse natation et injectées dans les stats de musculation.
    """
    assert resolve_sport(14001, has_sets=True) == "Natation"


@pytest.mark.parametrize(
    "code",
    [10004, 10005, 10011, 10013, 10019, 10020, 10022, 10023, 10024, 10026, 10027],
)
def test_strength_codes_map_to_musculation(code: int) -> None:
    assert resolve_sport(code, has_sets=True) == "Musculation"
    assert resolve_sport(code, has_sets=False) == "Musculation"


def test_custom_code_with_sets_is_musculation() -> None:
    """Le code 0 désigne une activité personnalisée : seul cas où la
    présence de séries tranche. 487 séances réelles sont dans ce cas."""
    assert resolve_sport(0, has_sets=True) == "Musculation"


def test_custom_code_without_sets_is_walking() -> None:
    """439 séances réelles. On conserve Marche pour ne pas casser la
    continuité des statistiques historiques."""
    assert resolve_sport(0, has_sets=False) == "Marche"


def test_unknown_code_is_labelled_not_dropped() -> None:
    """L'application Streamlit filtrait silencieusement les codes inconnus."""
    assert resolve_sport(99999, has_sets=False) == "Type 99999"


def test_missing_code_is_unknown() -> None:
    assert resolve_sport(None, has_sets=False) == "Inconnu"
