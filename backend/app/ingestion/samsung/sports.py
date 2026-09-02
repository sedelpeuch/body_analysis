"""Résolution du sport à partir du code d'exercice Samsung.

Ordre de résolution, cf. spec section 4.4. Le code fait foi ; la présence de
séries ne tranche que pour le code 0, seul code réellement ambigu.
"""

from __future__ import annotations

from types import MappingProxyType

CUSTOM_CODE = 0

SPORT_BY_CODE = MappingProxyType(
    {
        1001: "Marche",
        1002: "Course à pied",
        11007: "Vélo",
        13001: "Randonnée",
        14001: "Natation",
        15004: "Rameur",
        10025: "Poids du corps",
    }
)

STRENGTH_CODES = frozenset(
    {10004, 10005, 10011, 10013, 10019, 10020, 10022, 10023, 10024, 10026, 10027}
)

MUSCULATION = "Musculation"
WALKING = "Marche"
UNKNOWN = "Inconnu"


def resolve_sport(exercise_type: int | None, *, has_sets: bool) -> str:
    if exercise_type is None:
        return UNKNOWN
    known = SPORT_BY_CODE.get(exercise_type)
    if known is not None:
        return known
    if exercise_type in STRENGTH_CODES:
        return MUSCULATION
    if exercise_type == CUSTOM_CODE:
        return MUSCULATION if has_sets else WALKING
    return f"Type {exercise_type}"
